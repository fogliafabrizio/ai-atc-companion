import copy
import threading
import time
from dataclasses import dataclass, field

from src.udp_listener import UDPListener, XPlaneState


@dataclass
class Transmission:
    role: str
    text: str
    timestamp: float = field(default_factory=time.time)


class SessionManager:
    def __init__(self, udp_listener: UDPListener, poll_interval: float = 0.5) -> None:
        self._udp = udp_listener
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest_state: XPlaneState = XPlaneState()
        self._transmissions: list[Transmission] = []

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout)

    def get_udp_state(self) -> XPlaneState:
        with self._lock:
            return copy.copy(self._latest_state)

    def add_transmission(self, role: str, text: str) -> None:
        with self._lock:
            self._transmissions.append(Transmission(role=role, text=text))

    def get_transmissions(self) -> list[Transmission]:
        with self._lock:
            return list(self._transmissions)

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            state = self._udp.get_state()
            with self._lock:
                self._latest_state = state
            self._stop_event.wait(self._poll_interval)
