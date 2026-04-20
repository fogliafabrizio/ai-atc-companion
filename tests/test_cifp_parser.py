from pathlib import Path

import pytest

from src.cifp_parser import Procedure, ProcedureStep, get_procedures, parse_airport, _parse_lines

FIXTURES = Path(__file__).parent / "fixtures"
CIFP_FILE = FIXTURES / "LIML.dat"


def test_parse_returns_list():
    procs = parse_airport(CIFP_FILE)
    assert isinstance(procs, list)
    assert len(procs) > 0


def test_sids_found():
    procs = parse_airport(CIFP_FILE)
    sid_names = {p.name for p in procs if p.type == "SID"}
    assert "OPTO1E" in sid_names
    assert "KINES5" in sid_names


def test_stars_found():
    procs = parse_airport(CIFP_FILE)
    star_names = {p.name for p in procs if p.type == "STAR"}
    assert "GINA2A" in star_names
    assert "MAREN4" in star_names


def test_procedure_airport():
    procs = parse_airport(CIFP_FILE)
    for p in procs:
        assert p.airport == "LIML"


def test_opto1e_runway_transition():
    procs = parse_airport(CIFP_FILE)
    opto = next(p for p in procs if p.name == "OPTO1E")
    assert "36" in opto.runways()


def test_gina2a_runway_transition():
    procs = parse_airport(CIFP_FILE)
    gina = next(p for p in procs if p.name == "GINA2A")
    assert "16L" in gina.runways()


def test_opto1e_has_waypoints():
    procs = parse_airport(CIFP_FILE)
    opto = next(p for p in procs if p.name == "OPTO1E")
    fix_idents = [s.fix_ident for s in opto.steps]
    assert "OPTO" in fix_idents
    assert "MARIO" in fix_idents


def test_gina2a_has_waypoints():
    procs = parse_airport(CIFP_FILE)
    gina = next(p for p in procs if p.name == "GINA2A")
    fix_idents = [s.fix_ident for s in gina.steps]
    assert "GINA" in fix_idents
    assert "MAREN" in fix_idents


def test_runways_strips_rw_prefix():
    procs = parse_airport(CIFP_FILE)
    opto = next(p for p in procs if p.name == "OPTO1E")
    runways = opto.runways()
    assert all(not r.startswith("RW") for r in runways)


def test_get_procedures_by_icao():
    procs = get_procedures(FIXTURES, "LIML")
    assert len(procs) > 0
    assert all(p.airport == "LIML" for p in procs)


def test_get_procedures_missing_icao():
    procs = get_procedures(FIXTURES, "ZZZZ")
    assert procs == []


def test_parse_empty():
    procs = _parse_lines([])
    assert procs == []


def test_short_lines_skipped():
    lines = ["short", "S" * 37, "S" * 38 + "X" * 94]
    procs = _parse_lines(lines)
    assert procs == []


def test_non_airport_section_skipped():
    # Line with section='E' (ENROUTE) at col 4, not 'P' (airport)
    line = "SEUR" + "E" + "D" + "LIML" + "E" + "  " + "OPTO1E" + "OPTO1E" + " " + "010" + "LIML " + "EL" + "PG" + " " * 94
    procs = _parse_lines([line])
    assert procs == []


def test_procedure_step_sequence():
    procs = parse_airport(CIFP_FILE)
    opto = next(p for p in procs if p.name == "OPTO1E")
    common_steps = [s for s in opto.steps if s.transition == "OPTO1E"]
    seqs = [s.sequence for s in common_steps]
    assert seqs == sorted(seqs)
