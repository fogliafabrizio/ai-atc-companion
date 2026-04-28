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
    ) -> None:
        self._config = config
        self._stt = stt_engine
        self._tts = tts_engine
        self._output = audio_output
        self._router = controller_router
        self._session = session_manager
        self._ptt_active = threading.Event()
        self._processing = threading.Event()
        self._ptt_modifiers, self._ptt_trigger = self._parse_ptt_key(config.ptt_key)
        self._held_keys: set[object] = set()
        self._recording_buffer: list[np.ndarray] = []
        self._record_stream: object | None = None

    def _parse_ptt_key(self, key_str: str) -> tuple[set[object], object]:
        """Parse a key string into (modifier_set, trigger_key).

        Supports combo syntax: "ctrl+space" → ({Key.ctrl_l, Key.ctrl_r}, Key.space)
        Single key: "space" → (set(), Key.space)
        """
        import pynput.keyboard as kb

        parts = [p.strip() for p in key_str.lower().split("+")]
        trigger_str = parts[-1]
        modifier_strs = parts[:-1]

        def _parse_single(s: str) -> object:
            try:
                return kb.Key[s]
            except KeyError:
                return kb.KeyCode.from_char(s[0])

        modifiers: set[object] = set()
        for mod in modifier_strs:
            if mod in ("ctrl", "control"):
                modifiers.add(kb.Key.ctrl_l)
                modifiers.add(kb.Key.ctrl_r)
            elif mod in ("shift",):
                modifiers.add(kb.Key.shift_l)
                modifiers.add(kb.Key.shift_r)
            elif mod in ("alt",):
                modifiers.add(kb.Key.alt_l)
                modifiers.add(kb.Key.alt_r)
            else:
                modifiers.add(_parse_single(mod))

        trigger = _parse_single(trigger_str)
        return modifiers, trigger

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        self._recording_buffer.append(indata.copy())

    def _modifiers_active(self) -> bool:
        if not self._ptt_modifiers:
            return True
        return bool(self._held_keys & self._ptt_modifiers)

    def _on_press(self, key: object) -> None:
        import sounddevice as sd

        self._held_keys.add(key)

        if key != self._ptt_trigger or self._ptt_active.is_set():
            return
        if not self._modifiers_active():
            return
        if self._processing.is_set():
            print("[WARN] ATC is busy — wait for the response before transmitting.")
            return
        self._ptt_active.set()
        self._recording_buffer.clear()
        print("Recording...")
        try:
            self._record_stream = sd.InputStream(
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype="float32",
                device=self._config.input_device,
                callback=self._audio_callback,
            )
            self._record_stream.start()
        except Exception as exc:
            print(f"[ERROR] Recording failed: {exc}")
            self._ptt_active.clear()

    def _on_release(self, key: object) -> None:
        self._held_keys.discard(key)

        if key == self._ptt_trigger and self._ptt_active.is_set():
            self._ptt_active.clear()
            if self._record_stream is not None:
                self._record_stream.stop()
                self._record_stream.close()
                self._record_stream = None
            if self._recording_buffer:
                audio = np.concatenate(self._recording_buffer, axis=0).flatten()
                threading.Thread(target=self._process_transmission, args=(audio,), daemon=True).start()

    def _process_transmission(self, audio: np.ndarray) -> None:
        self._processing.set()
        try:
            print("Transcribing...")
            text = self._stt.transcribe(audio, self._config.sample_rate)
            if not text.strip():
                return
            print(f"[PILOT] {text}")
            self._session.add_transmission("pilot", text)
            reply = self._router.route_transmission(text)
            if reply is None:
                return
            print(f"[ATC]   {reply}")
            self._session.add_transmission("atc", reply)
            audio_bytes = self._tts.synthesize(reply)
            self._output.play(audio_bytes, _OPENAI_PCM_RATE)
        finally:
            self._processing.clear()

    def is_busy(self) -> bool:
        return self._processing.is_set() or self._ptt_active.is_set()

    def synthesize(self, text: str) -> bytes:
        return self._tts.synthesize(text)

    def play_atc(self, audio_bytes: bytes) -> None:
        self._output.play(audio_bytes, _OPENAI_PCM_RATE)

    def run(self) -> None:
        import pynput.keyboard as kb

        stop = threading.Event()

        def _on_release_with_stop(key: object) -> None:
            self._on_release(key)
            # pynput uses ESC as a conventional stop signal
            if key == kb.Key.esc:
                stop.set()

        with kb.Listener(on_press=self._on_press, on_release=_on_release_with_stop):
            try:
                while not stop.is_set():
                    stop.wait(timeout=0.1)
            except KeyboardInterrupt:
                pass
