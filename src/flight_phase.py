from enum import Enum

from src.udp_listener import XPlaneState


class FlightPhase(Enum):
    PARKED = "parked"
    TAXI = "taxi"
    TAKEOFF = "takeoff"
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"
    LANDING = "landing"


def infer_phase(state: XPlaneState) -> FlightPhase:
    if state.on_ground:
        if state.ground_speed_kts < 1.0:
            return FlightPhase.PARKED
        if state.ground_speed_kts >= 60.0:
            return FlightPhase.TAKEOFF
        return FlightPhase.TAXI
    if state.altitude_agl_ft < 500.0:
        return FlightPhase.LANDING
    if state.altitude_agl_ft < 3000.0 and state.vertical_speed_fpm < -200.0:
        return FlightPhase.APPROACH
    if state.vertical_speed_fpm > 300.0:
        return FlightPhase.CLIMB
    if state.vertical_speed_fpm < -300.0:
        return FlightPhase.DESCENT
    return FlightPhase.CRUISE
