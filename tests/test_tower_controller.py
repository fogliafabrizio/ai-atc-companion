from unittest.mock import MagicMock

import pytest

from src.controllers.tower import TowerContext, TowerController
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
def tower(mock_client: MagicMock, session: SessionManager, tmp_path) -> TowerController:
    skill_file = tmp_path / "tower_prompt.md"
    skill_file.write_text(
        "Role: {{ICAO}} rwy {{RUNWAY}}\n"
        "State: {{UDP_STATE}}\nHistory: {{TRANSMISSION_HISTORY}}\nPhase: {{FLIGHT_PHASE}}"
    )
    return TowerController(
        client=mock_client,
        session=session,
        context=TowerContext(icao="LIML", active_runway="36"),
        skill_path=str(skill_file),
    )


class TestTowerController:
    def test_respond_returns_string(self, tower: TowerController) -> None:
        result = tower.respond("ready for departure")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_respond_returns_mock_reply(
        self, tower: TowerController, mock_client: MagicMock
    ) -> None:
        assert tower.respond("ready for departure") == "ATC MOCK REPLY"

    def test_respond_calls_anthropic_api(
        self, tower: TowerController, mock_client: MagicMock
    ) -> None:
        tower.respond("ready for departure")
        mock_client.messages.create.assert_called_once()

    def test_system_prompt_contains_icao(
        self, tower: TowerController, mock_client: MagicMock
    ) -> None:
        tower.respond("ready for departure")
        system_text = "".join(
            b["text"] for b in mock_client.messages.create.call_args.kwargs["system"]
        )
        assert "LIML" in system_text

    def test_system_prompt_has_cache_control(
        self, tower: TowerController, mock_client: MagicMock
    ) -> None:
        tower.respond("ready for departure")
        blocks = mock_client.messages.create.call_args.kwargs["system"]
        assert any(b.get("cache_control", {}).get("type") == "ephemeral" for b in blocks)
