from typing import Protocol


class Controller(Protocol):
    def respond(self, text: str) -> str: ...


class MockController:
    _REPLY = "Callsign, roger. Standby."

    def respond(self, text: str) -> str:
        return self._REPLY


class ControllerRouter:
    def __init__(self, mock_controller: MockController | None = None) -> None:
        self._mock = mock_controller or MockController()

    def route_transmission(self, frequency: float, text: str) -> str:
        return self._mock.respond(text)
