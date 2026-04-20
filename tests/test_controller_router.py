import pytest

from src.controller_router import ControllerRouter, MockController


class TestMockController:
    def test_respond_returns_string(self) -> None:
        assert isinstance(MockController().respond("any text"), str)

    def test_respond_non_empty(self) -> None:
        assert len(MockController().respond("test")) > 0

    def test_respond_ignores_input(self) -> None:
        mc = MockController()
        assert mc.respond("hello") == mc.respond("goodbye")


class TestControllerRouter:
    def test_route_returns_string(self) -> None:
        assert isinstance(ControllerRouter().route_transmission(121.8, "test"), str)

    def test_route_non_empty_reply(self) -> None:
        assert ControllerRouter().route_transmission(121.8, "test") != ""

    def test_route_accepts_any_frequency(self) -> None:
        router = ControllerRouter()
        for freq in (118.7, 119.2, 121.8, 121.9, 125.9):
            assert isinstance(router.route_transmission(freq, "test"), str)

    def test_route_accepts_empty_text(self) -> None:
        assert isinstance(ControllerRouter().route_transmission(121.8, ""), str)

    def test_custom_mock_controller_injected(self) -> None:
        class StubController:
            def respond(self, text: str) -> str:
                return "STUB REPLY"

        router = ControllerRouter(mock_controller=StubController())
        assert router.route_transmission(121.8, "x") == "STUB REPLY"
