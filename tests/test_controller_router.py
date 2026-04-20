from unittest.mock import MagicMock

import pytest

from src.controller_router import ControllerRouter, MockController
from src.controllers.delivery import DeliveryContext, DeliveryController
from src.controllers.ground import GroundContext, GroundController
from src.controllers.tower import TowerContext, TowerController
from src.controllers.departure import DepartureContext, DepartureController
from src.controllers.approach import ApproachContext, ApproachController
from src.session_manager import SessionManager
from src.udp_listener import XPlaneState

FREQ_MAP = {
    121.8: "delivery",
    121.9: "ground",
    118.7: "tower",
    125.9: "departure",
    119.2: "approach",
}


def _make_session(freq: float) -> MagicMock:
    m = MagicMock(spec=SessionManager)
    m.active_frequency_mhz = freq
    m.get_flight_plan.return_value = None
    m.get_transmissions.return_value = []
    m.get_udp_state.return_value = XPlaneState()
    m.get_pilot_info.return_value = {"callsign": "", "company": ""}
    return m


def _make_mock_client() -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value.content = [MagicMock(text="ATC MOCK REPLY")]
    return client


def _make_skill(tmp_path, name: str = "prompt.md") -> str:
    skill = tmp_path / name
    skill.write_text("{{ICAO}} {{RUNWAY}} {{UDP_STATE}} {{TRANSMISSION_HISTORY}} {{FLIGHT_PHASE}}")
    return str(skill)


class TestMockController:
    def test_respond_returns_string(self) -> None:
        assert isinstance(MockController().respond("any text"), str)

    def test_respond_non_empty(self) -> None:
        assert len(MockController().respond("test")) > 0

    def test_respond_ignores_input(self) -> None:
        mc = MockController()
        assert mc.respond("hello") == mc.respond("goodbye")


class TestControllerRouter:
    def test_delivery_freq_routes_to_delivery(self, tmp_path) -> None:
        session = _make_session(121.8)
        client = _make_mock_client()
        dc = DeliveryController(
            client=client,
            session=session,
            context=DeliveryContext(icao="LIML", active_runway="36"),
            skill_path=_make_skill(tmp_path, "d.md"),
        )
        router = ControllerRouter(session=session, freq_map=FREQ_MAP, delivery_controller=dc)
        assert router.route_transmission("request clearance") == "ATC MOCK REPLY"

    def test_ground_freq_routes_to_ground(self, tmp_path) -> None:
        session = _make_session(121.9)
        client = _make_mock_client()
        gc = GroundController(
            client=client,
            session=session,
            context=GroundContext(icao="LIML", active_runway="36"),
            skill_path=_make_skill(tmp_path, "g.md"),
        )
        router = ControllerRouter(session=session, freq_map=FREQ_MAP, ground_controller=gc)
        assert router.route_transmission("ready to taxi") == "ATC MOCK REPLY"

    def test_tower_freq_routes_to_tower(self, tmp_path) -> None:
        session = _make_session(118.7)
        client = _make_mock_client()
        tc = TowerController(
            client=client,
            session=session,
            context=TowerContext(icao="LIML", active_runway="36"),
            skill_path=_make_skill(tmp_path, "t.md"),
        )
        router = ControllerRouter(session=session, freq_map=FREQ_MAP, tower_controller=tc)
        assert router.route_transmission("ready for departure") == "ATC MOCK REPLY"

    def test_departure_freq_routes_to_departure(self, tmp_path) -> None:
        session = _make_session(125.9)
        client = _make_mock_client()
        dep = DepartureController(
            client=client,
            session=session,
            context=DepartureContext(icao="LIML", active_runway="36"),
            skill_path=_make_skill(tmp_path, "dep.md"),
        )
        router = ControllerRouter(session=session, freq_map=FREQ_MAP, departure_controller=dep)
        assert router.route_transmission("airborne") == "ATC MOCK REPLY"

    def test_approach_freq_routes_to_approach(self, tmp_path) -> None:
        session = _make_session(119.2)
        client = _make_mock_client()
        app = ApproachController(
            client=client,
            session=session,
            context=ApproachContext(icao="LIML", active_runway="36"),
            skill_path=_make_skill(tmp_path, "app.md"),
        )
        router = ControllerRouter(session=session, freq_map=FREQ_MAP, approach_controller=app)
        assert router.route_transmission("descending") == "ATC MOCK REPLY"

    def test_unknown_freq_falls_back_to_mock(self) -> None:
        session = _make_session(136.0)
        router = ControllerRouter(session=session, freq_map=FREQ_MAP)
        result = router.route_transmission("test")
        assert isinstance(result, str) and len(result) > 0

    def test_no_controller_registered_falls_back_to_mock(self) -> None:
        session = _make_session(121.8)
        router = ControllerRouter(session=session, freq_map=FREQ_MAP)
        result = router.route_transmission("request clearance")
        assert isinstance(result, str) and len(result) > 0

    def test_custom_fallback_controller(self) -> None:
        class StubController:
            def respond(self, text: str) -> str:
                return "STUB REPLY"

        session = _make_session(136.0)
        router = ControllerRouter(
            session=session, freq_map=FREQ_MAP, fallback_controller=StubController()
        )
        assert router.route_transmission("anything") == "STUB REPLY"

    def test_empty_freq_map_always_falls_back(self) -> None:
        session = _make_session(121.8)
        router = ControllerRouter(session=session, freq_map={})
        assert isinstance(router.route_transmission("test"), str)
