import threading
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from src.controller_router import ControllerRouter
from src.session_manager import SessionManager

_OPENAI_PCM_RATE = 24000


class STTEngine(Protocol):
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str: ...


class TTSEngine(Protocol):
    def synthesize(self, text: str) -> bytes: ...


class AudioOutput(Protocol):
    def play(self, audio_bytes: bytes, sample_rate: int) -> None: ...


class WhisperSTT:
    def __init__(self, model_size: str = "base") -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        segments, _ = self._model.transcribe(audio, language="en")
        return " ".join(s.text.strip() for s in segments)


class OpenAITTS:
    def __init__(self, client: object, voice: str = "onyx") -> None:
        self._client = client
        self._voice = voice

    def synthesize(self, text: str) -> bytes:
        response = self._client.audio.speech.create(
            model="tts-1",
            voice=self._voice,
            input=text,
            response_format="pcm",
        )
        return response.content


class SounddeviceOutput:
    def __init__(self, device: str | int | None = None) -> None:
        self._device = device

    def play(self, audio_bytes: bytes, sample_rate: int) -> None:
        import sounddevice as sd

        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio, samplerate=sample_rate, device=self._device)
        sd.wait()


@dataclass
class AudioConfig:
    ptt_key: str
    input_device: str | int | None
    output_device: str | int | None
    sample_rate: int
    channels: int


class AudioPipeline:
    def __init__(
        self,
        config: AudioConfig,
        stt_engine: STTEngine,
        tts_engine: TTSEngine,
        audio_output: AudioOutput,
        controller_router: ControllerRouter,
        session_manager: SessionManager,
        frequency: float = 121.8,
    ) -> None:
        self._config = config
        self._stt = stt_engine
        self._tts = tts_engine
        self._output = audio_output
        self._router = controller_router
        self._session = session_manager
        self._frequency = frequency
        self._ptt_active = threading.Event()
        self._ptt_key = self._parse_ptt_key(config.ptt_key)
        self._recording_buffer: list[np.ndarray] = []
        self._record_stream: object | None = None

    def _parse_ptt_key(self, key_str: str) -> object:
        import pynput.keyboard as kb

        try:
            return kb.Key[key_str]
        except KeyError:
            return kb.KeyCode.from_char(key_str[0])

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        self._recording_buffer.append(indata.copy())

    def _on_press(self, key: object) -> None:
        import sounddevice as sd

        if key == self._ptt_key and not self._ptt_active.is_set():
            self._ptt_active.set()
            self._recording_buffer.clear()
            self._record_stream = sd.InputStream(
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype="float32",
                device=self._config.input_device,
                callback=self._audio_callback,
            )
            self._record_stream.start()

    def _on_release(self, key: object) -> None:
        if key == self._ptt_key and self._ptt_active.is_set():
            self._ptt_active.clear()
            if self._record_stream is not None:
                self._record_stream.stop()
                self._record_stream.close()
                self._record_stream = None
            if self._recording_buffer:
                audio = np.concatenate(self._recording_buffer, axis=0).flatten()
                self._process_transmission(audio)

    def _process_transmission(self, audio: np.ndarray) -> None:
        text = self._stt.transcribe(audio, self._config.sample_rate)
        if not text.strip():
            return
        self._session.add_transmission("pilot", text)
        reply = self._router.route_transmission(self._frequency, text)
        self._session.add_transmission("atc", reply)
        audio_bytes = self._tts.synthesize(reply)
        self._output.play(audio_bytes, _OPENAI_PCM_RATE)

    def run(self) -> None:
        import pynput.keyboard as kb

        with kb.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            listener.join()
