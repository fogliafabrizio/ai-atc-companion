from unittest.mock import MagicMock, patch

import pytest

from src.controller_router import ControllerRouter, DELIVERY_FREQ
from src.controllers.delivery import DeliveryContext, DeliveryController
from src.session_manager import SessionManager
from src.udp_listener import XPlaneState


class StubUDPListener:
    def get_state(self) -> XPlaneState:
        return XPlaneState()

    def start(self) -> None:
        pass

    def stop(self, timeout: float = 2.0) -> None:
        pass


@pytest.fixture
def session() -> SessionManager:
    sm = SessionManager(udp_listener=StubUDPListener(), poll_interval=0.05)
    sm.start()
    yield sm
    sm.stop()


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value.content = [MagicMock(text="ATC MOCK REPLY")]
    return client


@pytest.fixture
def delivery(mock_client: MagicMock, session: SessionManager, tmp_path) -> DeliveryController:
    skill_file = tmp_path / "controller_prompt.md"
    skill_file.write_text(
        "Role: {{ICAO}} rwy {{RUNWAY}}\nState: {{UDP_STATE}}\nHistory: {{TRANSMISSION_HISTORY}}"
    )
    return DeliveryController(
        client=mock_client,
        session=session,
        context=DeliveryContext(icao="LIML", active_runway="36"),
        skill_path=str(skill_file),
    )


class TestDeliveryController:
    def test_respond_returns_string(self, delivery: DeliveryController) -> None:
        result = delivery.respond("request IFR clearance")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_respond_returns_mock_client_text(
        self, delivery: DeliveryController, mock_client: MagicMock
    ) -> None:
        result = delivery.respond("request IFR clearance")
        assert result == "ATC MOCK REPLY"

    def test_respond_calls_anthropic_api(
        self, delivery: DeliveryController, mock_client: MagicMock
    ) -> None:
        delivery.respond("request IFR clearance")
        mock_client.messages.create.assert_called_once()

    def test_system_prompt_contains_icao(
        self, delivery: DeliveryController, mock_client: MagicMock
    ) -> None:
        delivery.respond("request IFR clearance")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        system_blocks = call_kwargs["system"]
        system_text = "".join(b["text"] for b in system_blocks)
        assert "LIML" in system_text

    def test_system_prompt_contains_runway(
        self, delivery: DeliveryController, mock_client: MagicMock
    ) -> None:
        delivery.respond("request IFR clearance")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        system_text = "".join(b["text"] for b in call_kwargs["system"])
        assert "36" in system_text

    def test_system_prompt_has_cache_control(
        self, delivery: DeliveryController, mock_client: MagicMock
    ) -> None:
        delivery.respond("request IFR clearance")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        system_blocks = call_kwargs["system"]
        assert any(b.get("cache_control", {}).get("type") == "ephemeral" for b in system_blocks)

    def test_messages_include_pilot_text(
        self, delivery: DeliveryController, mock_client: MagicMock
    ) -> None:
        delivery.respond("request IFR clearance")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        last_msg = messages[-1]
        assert last_msg["role"] == "user"
        assert "request IFR clearance" in last_msg["content"]

    def test_transmission_history_included_in_messages(
        self, delivery: DeliveryController, session: SessionManager, mock_client: MagicMock
    ) -> None:
        session.add_transmission("pilot", "ready to copy")
        session.add_transmission("atc", "standby")
        delivery.respond("request IFR clearance")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        contents = [m["content"] for m in messages]
        assert any("ready to copy" in c for c in contents)
        assert any("standby" in c for c in contents)

    def test_messages_end_with_user_role(
        self, delivery: DeliveryController, mock_client: MagicMock
    ) -> None:
        delivery.respond("anything")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["messages"][-1]["role"] == "user"

    def test_empty_session_history_still_works(
        self, delivery: DeliveryController
    ) -> None:
        result = delivery.respond("request IFR clearance")
        assert isinstance(result, str)


class TestRouterWithDelivery:
    def test_delivery_freq_routes_to_delivery_controller(
        self, mock_client: MagicMock, session: SessionManager, tmp_path
    ) -> None:
        skill_file = tmp_path / "p.md"
        skill_file.write_text("{{ICAO}} {{RUNWAY}} {{UDP_STATE}} {{TRANSMISSION_HISTORY}}")
        dc = DeliveryController(
            client=mock_client,
            session=session,
            context=DeliveryContext(icao="LIML", active_runway="36"),
            skill_path=str(skill_file),
        )
        router = ControllerRouter(delivery_controller=dc)
        result = router.route_transmission(DELIVERY_FREQ, "request clearance")
        assert result == "ATC MOCK REPLY"

    def test_other_freq_falls_back_to_mock(
        self, mock_client: MagicMock, session: SessionManager, tmp_path
    ) -> None:
        skill_file = tmp_path / "p.md"
        skill_file.write_text("{{ICAO}} {{RUNWAY}} {{UDP_STATE}} {{TRANSMISSION_HISTORY}}")
        dc = DeliveryController(
            client=mock_client,
            session=session,
            context=DeliveryContext(icao="LIML", active_runway="36"),
            skill_path=str(skill_file),
        )
        router = ControllerRouter(delivery_controller=dc)
        result = router.route_transmission(121.9, "taxi request")
        assert result != "ATC MOCK REPLY"
        assert isinstance(result, str)

    def test_no_delivery_controller_uses_mock(self) -> None:
        router = ControllerRouter()
        result = router.route_transmission(DELIVERY_FREQ, "request clearance")
        assert isinstance(result, str)
        assert len(result) > 0
