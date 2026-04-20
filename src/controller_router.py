from typing import Protocol

from src.session_manager import SessionManager


class Controller(Protocol):
    def respond(self, text: str) -> str: ...


class MockController:
    _REPLY = "Callsign, roger. Standby."

    def respond(self, text: str) -> str:
        return self._REPLY


class ControllerRouter:
    def __init__(
        self,
        session: SessionManager,
        freq_map: dict[float, str],
        *,
        delivery_controller: Controller | None = None,
        ground_controller: Controller | None = None,
        tower_controller: Controller | None = None,
        departure_controller: Controller | None = None,
        approach_controller: Controller | None = None,
        fallback_controller: Controller | None = None,
    ) -> None:
        self._session = session
        self._freq_map = freq_map
        self._controllers: dict[str, Controller] = {}
        for role, ctrl in [
            ("delivery", delivery_controller),
            ("ground", ground_controller),
            ("tower", tower_controller),
            ("departure", departure_controller),
            ("approach", approach_controller),
        ]:
            if ctrl is not None:
                self._controllers[role] = ctrl
        self._fallback = fallback_controller

    def route_transmission(self, text: str) -> str | None:
        freq = self._session.active_frequency_mhz
        role = self._freq_to_role(freq)
        controller = self._controllers.get(role) or self._fallback
        if controller is None:
            if freq == 0.0:
                print("[WARN] No active frequency (X-Plane not connected) — transmission ignored.")
            else:
                print(f"[WARN] freq={freq:.3f} MHz not assigned to any controller — using mock fallback.")
            return MockController().respond(text)
        return controller.respond(text)

    def active_controller(self) -> object | None:
        freq = self._session.active_frequency_mhz
        role = self._freq_to_role(freq)
        return self._controllers.get(role) or self._fallback

    def _freq_to_role(self, freq: float) -> str:
        for map_freq, role in self._freq_map.items():
            if abs(freq - map_freq) < 0.005:  # ±5 kHz tolerance
                return role
        return ""
