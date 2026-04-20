from pathlib import Path

import pytest

from src.fms_reader import FlightPlan, Waypoint, parse, _parse_lines

FIXTURES = Path(__file__).parent / "fixtures"
FMS_FILE = FIXTURES / "LIML_IFR_LIRF.fms"


def test_parse_returns_flight_plan():
    fp = parse(FMS_FILE)
    assert isinstance(fp, FlightPlan)


def test_departure_arrival():
    fp = parse(FMS_FILE)
    assert fp.departure == "LIML"
    assert fp.arrival == "LIRF"


def test_runways():
    fp = parse(FMS_FILE)
    assert fp.dep_runway == "36"
    assert fp.arr_runway == "16L"


def test_procedures():
    fp = parse(FMS_FILE)
    assert fp.sid == "OPTO1E"
    assert fp.star == "GINA2A"
    assert fp.approach == "I16L"


def test_cycle():
    fp = parse(FMS_FILE)
    assert fp.cycle == "2312"


def test_waypoints_count():
    fp = parse(FMS_FILE)
    assert len(fp.waypoints) == 8


def test_waypoints_content():
    fp = parse(FMS_FILE)
    idents = [w.ident for w in fp.waypoints]
    assert idents[0] == "LIML"
    assert idents[-1] == "LIRF"
    assert "OPTO" in idents
    assert "SOGMI" in idents


def test_waypoint_types():
    fp = parse(FMS_FILE)
    assert fp.waypoints[0].type == 1   # airport
    assert fp.waypoints[-1].type == 1  # airport
    assert fp.waypoints[1].type == 11  # named fix


def test_cruise_fl():
    fp = parse(FMS_FILE)
    assert fp.cruise_fl == 240  # max alt = 24000 ft → FL240


def test_waypoint_coordinates():
    fp = parse(FMS_FILE)
    liml = fp.waypoints[0]
    assert abs(liml.lat - 45.445083) < 0.001
    assert abs(liml.lon - 9.276750) < 0.001


def test_parse_empty():
    fp = _parse_lines([])
    assert fp.departure == ""
    assert fp.waypoints == []


def test_parse_v1100_no_sid():
    lines = [
        "I",
        "1100 Version",
        "ADEP XXXX",
        "ADES YYYY",
        "NUMENR 2",
        "1 XXXX ADEP 0.000000 10.0 20.0",
        "1 YYYY ADES 0.000000 11.0 21.0",
    ]
    fp = _parse_lines(lines)
    assert fp.departure == "XXXX"
    assert fp.arrival == "YYYY"
    assert fp.sid == ""
    assert fp.cruise_fl == 0


def test_sidtrans_not_parsed_as_sid():
    lines = [
        "I",
        "1100 Version",
        "ADEP LIML",
        "SID OPTO1E",
        "SIDTRANS --",
        "ADES LIRF",
        "NUMENR 0",
    ]
    fp = _parse_lines(lines)
    assert fp.sid == "OPTO1E"


def test_startrans_not_parsed_as_star():
    lines = [
        "I",
        "1100 Version",
        "ADEP LIML",
        "ADES LIRF",
        "STAR GINA2A",
        "STARTRANS --",
        "NUMENR 0",
    ]
    fp = _parse_lines(lines)
    assert fp.star == "GINA2A"
