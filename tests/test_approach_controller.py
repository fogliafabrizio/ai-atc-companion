from unittest.mock import MagicMock

import pytest

from src.controllers.approach import ApproachContext, ApproachController
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
def approach(mock_client: MagicMock, session: SessionManager, tmp_path) -> ApproachController:
    skill_file = tmp_path / "approach_prompt.md"
    skill_file.write_text(
        "Role: {{ICAO}} rwy {{RUNWAY}} {{APPROACH_TYPE}}\n"
        "State: {{UDP_STATE}}\nHistory: {{TRANSMISSION_HISTORY}}\nPhase: {{FLIGHT_PHASE}}"
    )
    return ApproachController(
        client=mock_client,
        session=session,
        context=ApproachContext(icao="LIML", active_runway="36", approach_type="ILS"),
        skill_path=str(skill_file),
    )


class TestApproachController:
    def test_respond_returns_string(self, approach: ApproachController) -> None:
        result = approach.respond("descending to flight level one eight zero")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_respond_returns_mock_reply(
        self, approach: ApproachController, mock_client: MagicMock
    ) -> None:
        assert approach.respond("descending to flight level one eight zero") == "ATC MOCK REPLY"

    def test_respond_calls_anthropic_api(
        self, approach: ApproachController, mock_client: MagicMock
    ) -> None:
        approach.respond("descending to flight level one eight zero")
        mock_client.messages.create.assert_called_once()

    def test_system_prompt_contains_icao(
        self, approach: ApproachController, mock_client: MagicMock
    ) -> None:
        approach.respond("descending to flight level one eight zero")
        system_text = "".join(
            b["text"] for b in mock_client.messages.create.call_args.kwargs["system"]
        )
        assert "LIML" in system_text

    def test_system_prompt_has_cache_control(
        self, approach: ApproachController, mock_client: MagicMock
    ) -> None:
        approach.respond("descending to flight level one eight zero")
        blocks = mock_client.messages.create.call_args.kwargs["system"]
        assert any(b.get("cache_control", {}).get("type") == "ephemeral" for b in blocks)

    def test_system_prompt_contains_approach_type(
        self, approach: ApproachController, mock_client: MagicMock
    ) -> None:
        approach.respond("descending to flight level one eight zero")
        system_text = "".join(
            b["text"] for b in mock_client.messages.create.call_args.kwargs["system"]
        )
        assert "ILS" in system_text
