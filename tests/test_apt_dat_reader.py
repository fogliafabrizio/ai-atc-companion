from __future__ import annotations

from pathlib import Path

import pytest

from src.apt_dat_reader import get_apt_dat_path, get_frequencies

FIXTURES = Path(__file__).parent / "fixtures"
APT_DAT = FIXTURES / "apt_liml.dat"

_EXPECTED_LIML = {
    118.0: "atis",
    121.8: "delivery",
    121.9: "ground",
    118.7: "tower",
    119.2: "approach",
    125.9: "departure",
}


class TestGetFrequencies:
    def test_returns_dict(self) -> None:
        assert isinstance(get_frequencies(APT_DAT, "LIML"), dict)

    def test_liml_delivery_frequency(self) -> None:
        result = get_frequencies(APT_DAT, "LIML")
        assert result[121.8] == "delivery"

    def test_liml_all_six_frequencies(self) -> None:
        result = get_frequencies(APT_DAT, "LIML")
        assert result == _EXPECTED_LIML

    def test_unknown_icao_returns_empty_dict(self) -> None:
        assert get_frequencies(APT_DAT, "ZZZZ") == {}

    def test_stops_at_next_airport_boundary(self) -> None:
        # EGLL Tower is 118.7 — same freq as LIML Tower. The LIML result must
        # not contain a second entry for it sourced from EGLL's section.
        result = get_frequencies(APT_DAT, "LIML")
        # Exactly six entries — no bleed from EGLL
        assert len(result) == 6

    def test_case_insensitive_icao(self) -> None:
        assert get_frequencies(APT_DAT, "liml") == get_frequencies(APT_DAT, "LIML")

    def test_frequency_keys_are_float(self) -> None:
        result = get_frequencies(APT_DAT, "LIML")
        assert all(isinstance(k, float) for k in result)


class TestGetAptDatPath:
    def test_builds_correct_path(self) -> None:
        path = get_apt_dat_path("C:/XPlane12")
        normalized = str(path).replace("\\", "/")
        assert normalized.endswith(
            "Resources/default scenery/default apt dat/Earth nav data/apt.dat"
        )

    def test_accepts_path_object(self) -> None:
        path = get_apt_dat_path(Path("C:/XPlane12"))
        assert isinstance(path, Path)
