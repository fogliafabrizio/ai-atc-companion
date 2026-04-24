from unittest.mock import MagicMock

import pytest

from src.controllers.ground import GroundContext, GroundController
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
def ground(mock_client: MagicMock, session: SessionManager, tmp_path) -> GroundController:
    skill_file = tmp_path / "ground_prompt.md"
    skill_file.write_text(
        "Role: {{ICAO}} rwy {{RUNWAY}} {{DEP_OR_ARR}}\n"
        "State: {{UDP_STATE}}\nHistory: {{TRANSMISSION_HISTORY}}\nPhase: {{FLIGHT_PHASE}}"
    )
    return GroundController(
        client=mock_client,
        session=session,
        context=GroundContext(icao="LIML", active_runway="36", dep_or_arr="departure"),
        skill_path=str(skill_file),
    )


class TestGroundController:
    def test_respond_returns_string(self, ground: GroundController) -> None:
        result = ground.respond("request taxi")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_respond_returns_mock_reply(
        self, ground: GroundController, mock_client: MagicMock
    ) -> None:
        assert ground.respond("request taxi") == "ATC MOCK REPLY"

    def test_respond_calls_anthropic_api(
        self, ground: GroundController, mock_client: MagicMock
    ) -> None:
        ground.respond("request taxi")
        mock_client.messages.create.assert_called_once()

    def test_system_prompt_contains_icao(
        self, ground: GroundController, mock_client: MagicMock
    ) -> None:
        ground.respond("request taxi")
        system_text = "".join(
            b["text"] for b in mock_client.messages.create.call_args.kwargs["system"]
        )
        assert "LIML" in system_text

    def test_system_prompt_has_cache_control(
        self, ground: GroundController, mock_client: MagicMock
    ) -> None:
        ground.respond("request taxi")
        blocks = mock_client.messages.create.call_args.kwargs["system"]
        assert any(b.get("cache_control", {}).get("type") == "ephemeral" for b in blocks)

    def test_system_prompt_contains_dep_or_arr(
        self, ground: GroundController, mock_client: MagicMock
    ) -> None:
        ground.respond("request taxi")
        system_text = "".join(
            b["text"] for b in mock_client.messages.create.call_args.kwargs["system"]
        )
        assert "departure" in system_text
