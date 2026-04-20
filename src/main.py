import signal
import sys

import openai
import yaml
from dotenv import load_dotenv

from src.audio_pipeline import (
    AudioConfig,
    AudioPipeline,
    OpenAITTS,
    SounddeviceOutput,
    WhisperSTT,
)
from src.controller_router import ControllerRouter
from src.session_manager import SessionManager
from src.udp_listener import UDPListener


def _load_settings(path: str = "config/settings.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    load_dotenv()
    settings = _load_settings()

    udp_cfg = settings.get("udp", {})
    audio_cfg = settings.get("audio", {})

    config = AudioConfig(
        ptt_key=audio_cfg.get("ptt_key", "space"),
        input_device=audio_cfg.get("input_device"),
        output_device=audio_cfg.get("output_device"),
        sample_rate=audio_cfg.get("sample_rate", 16000),
        channels=audio_cfg.get("channels", 1),
    )

    udp_listener = UDPListener(port=udp_cfg.get("port", 49100))
    udp_listener.start()

    session = SessionManager(udp_listener)
    session.start()

    router = ControllerRouter()

    # Instantiate WhisperSTT before entering the PTT loop so the model
    # download (if needed) happens at startup, not mid-transmission.
    stt = WhisperSTT(model_size=audio_cfg.get("whisper_model_size", "base"))
    tts = OpenAITTS(client=openai.OpenAI())
    output = SounddeviceOutput(device=config.output_device)

    pipeline = AudioPipeline(
        config=config,
        stt_engine=stt,
        tts_engine=tts,
        audio_output=output,
        controller_router=router,
        session_manager=session,
    )

    def _shutdown(sig: int, frame: object) -> None:
        print("\nShutting down...")
        session.stop()
        udp_listener.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print(f"PTT key: [{config.ptt_key}]  |  Press Ctrl-C to exit.")
    pipeline.run()


if __name__ == "__main__":
    main()
