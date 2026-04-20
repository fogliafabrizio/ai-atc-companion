from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.udp_listener import UDPListener, XPlaneState

if TYPE_CHECKING:
    from src.fms_reader import FlightPlan


_AIRLINE_CODES: dict[str, str] = {
    "AAL": "AMERICAN",
    "AFR": "AIR FRANCE",
    "AUA": "AUSTRIAN",
    "AZA": "ALITALIA",
    "BAW": "SPEEDBIRD",
    "BEL": "BRUSSELS",
    "DAL": "DELTA",
    "DLH": "LUFTHANSA",
    "EZY": "EASYJET",
    "IBE": "IBERIA",
    "KLM": "KLM",
    "NJE": "NETJETS",
    "RYR": "RYANAIR",
    "SWR": "SWISS",
    "TAP": "TAP AIR PORTUGAL",
    "UAE": "EMIRATES",
    "UAL": "UNITED",
    "VLG": "VUELING",
    "WZZ": "WIZZ AIR",
}


def _resolve_company(callsign: str) -> str:
    if len(callsign) >= 3:
        return _AIRLINE_CODES.get(callsign[:3].upper(), "")
    return ""


@dataclass
class Transmission:
    role: str
    text: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionEvent:
    kind: str
    payload: dict
    timestamp: float = field(default_factory=time.time)


class SessionManager:
    def __init__(
        self,
        udp_listener: UDPListener,
        poll_interval: float = 0.5,
        pilot_callsign: str = "",
        pilot_company: str = "",
    ) -> None:
        self._udp = udp_listener
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest_state: XPlaneState = XPlaneState()
        self._transmissions: list[Transmission] = []
        self._flight_plan: FlightPlan | None = None
        self._pilot_callsign = pilot_callsign
        self._pilot_company = pilot_company or _resolve_company(pilot_callsign)
        self._active_frequency_mhz: float = 0.0
        self._events: list[SessionEvent] = []

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

    def set_flight_plan(self, fp: FlightPlan) -> None:
        with self._lock:
            self._flight_plan = fp

    def get_flight_plan(self) -> FlightPlan | None:
        with self._lock:
            return self._flight_plan

    def get_pilot_info(self) -> dict[str, str]:
        with self._lock:
            return {"callsign": self._pilot_callsign, "company": self._pilot_company}

    @property
    def active_frequency_mhz(self) -> float:
        with self._lock:
            return self._active_frequency_mhz

    def log_event(self, kind: str, payload: dict) -> None:
        with self._lock:
            self._events.append(SessionEvent(kind=kind, payload=payload))

    def get_events(self) -> list[SessionEvent]:
        with self._lock:
            return list(self._events)

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            state = self._udp.get_state()
            freq_change: tuple[float, float] | None = None
            with self._lock:
                self._latest_state = state
                new_freq = state.com1_freq_mhz
                if new_freq > 0 and new_freq != self._active_frequency_mhz:
                    freq_change = (self._active_frequency_mhz, new_freq)
                    self._active_frequency_mhz = new_freq
            if freq_change:
                self.log_event("freq_change", {"from_mhz": freq_change[0], "to_mhz": freq_change[1]})
                print(f"[SessionManager] COM1: {freq_change[0]:.2f} → {freq_change[1]:.2f} MHz")
            self._stop_event.wait(self._poll_interval)
