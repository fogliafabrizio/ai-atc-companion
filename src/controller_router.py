from typing import Protocol

DELIVERY_FREQ = 121.8


class Controller(Protocol):
    def respond(self, text: str) -> str: ...


class MockController:
    _REPLY = "Callsign, roger. Standby."

    def respond(self, text: str) -> str:
        return self._REPLY


class ControllerRouter:
    def __init__(
        self,
        mock_controller: MockController | None = None,
        delivery_controller: Controller | None = None,
    ) -> None:
        self._mock = mock_controller or MockController()
        self._delivery = delivery_controller

    def route_transmission(self, frequency: float, text: str) -> str:
        if self._delivery and abs(frequency - DELIVERY_FREQ) < 0.05:
            return self._delivery.respond(text)
        return self._mock.respond(text)
