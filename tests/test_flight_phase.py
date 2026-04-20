import pytest

from src.flight_phase import FlightPhase, infer_phase
from src.udp_listener import XPlaneState


def _state(**kwargs) -> XPlaneState:
    return XPlaneState(**kwargs)


class TestInferPhase:
    def test_parked(self) -> None:
        state = _state(on_ground=True, ground_speed_kts=0.0)
        assert infer_phase(state) == FlightPhase.PARKED

    def test_parked_low_speed(self) -> None:
        state = _state(on_ground=True, ground_speed_kts=0.5)
        assert infer_phase(state) == FlightPhase.PARKED

    def test_taxi(self) -> None:
        state = _state(on_ground=True, ground_speed_kts=15.0)
        assert infer_phase(state) == FlightPhase.TAXI

    def test_takeoff_roll(self) -> None:
        state = _state(on_ground=True, ground_speed_kts=80.0)
        assert infer_phase(state) == FlightPhase.TAKEOFF

    def test_landing(self) -> None:
        state = _state(on_ground=False, altitude_agl_ft=100.0, vertical_speed_fpm=-500.0)
        assert infer_phase(state) == FlightPhase.LANDING

    def test_approach(self) -> None:
        state = _state(on_ground=False, altitude_agl_ft=2000.0, vertical_speed_fpm=-500.0)
        assert infer_phase(state) == FlightPhase.APPROACH

    def test_climb(self) -> None:
        state = _state(on_ground=False, altitude_agl_ft=5000.0, vertical_speed_fpm=1500.0)
        assert infer_phase(state) == FlightPhase.CLIMB

    def test_descent(self) -> None:
        state = _state(on_ground=False, altitude_agl_ft=20000.0, vertical_speed_fpm=-1000.0)
        assert infer_phase(state) == FlightPhase.DESCENT

    def test_cruise(self) -> None:
        state = _state(on_ground=False, altitude_agl_ft=35000.0, vertical_speed_fpm=50.0)
        assert infer_phase(state) == FlightPhase.CRUISE
