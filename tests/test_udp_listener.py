"""
Unit tests for src/udp_listener.py.

No actual network connection is required — tests call parse_data_packet()
directly with hand-crafted binary payloads.
"""

from __future__ import annotations

import struct
import time

import pytest

from src.udp_listener import (
    XPlaneState,
    _GROUP_FORMAT,
    _GROUP_SIZE,
    _HEADER,
    _ON_GROUND_AGL_FT,
    _ROW_GPS,
    _ROW_SPEEDS,
    _ROW_VSPEED,
    parse_data_packet,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_group(row_index: int, *values: float) -> bytes:
    """Pack a single 36-byte DATA group with up to 8 float values."""
    padded = list(values) + [0.0] * (8 - len(values))
    return struct.pack(_GROUP_FORMAT, row_index, *padded[:8])


def _make_packet(*groups: bytes) -> bytes:
    """Assemble a complete DATA packet from pre-packed group bytes."""
    return _HEADER + b"".join(groups)


# ---------------------------------------------------------------------------
# parse_data_packet — core parsing
# ---------------------------------------------------------------------------


class TestParseDataPacket:
    def test_returns_none_for_bad_header(self) -> None:
        bad = b"XATP\x00" + _make_group(_ROW_GPS, 45.0, 9.0, 1000.0, 50.0)
        assert parse_data_packet(bad) is None

    def test_returns_none_for_empty_packet(self) -> None:
        assert parse_data_packet(b"") is None

    def test_returns_xplanestate_instance(self) -> None:
        pkt = _make_packet(_make_group(_ROW_GPS, 45.0, 9.0, 1000.0, 50.0))
        result = parse_data_packet(pkt)
        assert isinstance(result, XPlaneState)

    def test_parses_gps_row(self) -> None:
        lat, lon, msl, agl = 45.464161, 9.191778, 2500.0, 2450.0
        pkt = _make_packet(_make_group(_ROW_GPS, lat, lon, msl, agl))
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.latitude == pytest.approx(lat, rel=1e-5)
        assert s.longitude == pytest.approx(lon, rel=1e-5)
        assert s.altitude_msl_ft == pytest.approx(msl, rel=1e-5)
        assert s.altitude_agl_ft == pytest.approx(agl, rel=1e-5)

    def test_parses_vertical_speed_row(self) -> None:
        vspd = -500.0
        pkt = _make_packet(_make_group(_ROW_VSPEED, 0.0, vspd))
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.vertical_speed_fpm == pytest.approx(vspd, rel=1e-5)

    def test_parses_ground_speed_row(self) -> None:
        gs = 130.5
        pkt = _make_packet(_make_group(_ROW_SPEEDS, 0.0, 0.0, 0.0, gs))
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.ground_speed_kts == pytest.approx(gs, rel=1e-5)

    def test_parses_all_three_rows_together(self) -> None:
        lat, lon, msl, agl = 51.477928, -0.001545, 3000.0, 2950.0
        vspd = 1200.0
        gs = 145.0
        pkt = _make_packet(
            _make_group(_ROW_GPS, lat, lon, msl, agl),
            _make_group(_ROW_VSPEED, 0.0, vspd),
            _make_group(_ROW_SPEEDS, 0.0, 0.0, 0.0, gs),
        )
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.latitude == pytest.approx(lat, rel=1e-5)
        assert s.longitude == pytest.approx(lon, rel=1e-5)
        assert s.altitude_msl_ft == pytest.approx(msl, rel=1e-5)
        assert s.altitude_agl_ft == pytest.approx(agl, rel=1e-5)
        assert s.vertical_speed_fpm == pytest.approx(vspd, rel=1e-5)
        assert s.ground_speed_kts == pytest.approx(gs, rel=1e-5)

    def test_ignores_unknown_rows(self) -> None:
        pkt = _make_packet(_make_group(99, 1.0, 2.0, 3.0, 4.0))
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.latitude == 0.0
        assert s.ground_speed_kts == 0.0

    def test_tolerates_truncated_trailing_bytes(self) -> None:
        valid_group = _make_group(_ROW_GPS, 10.0, 20.0, 5000.0, 4900.0)
        pkt = _HEADER + valid_group + b"\xff\xff\xff\xff\xff"
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.latitude == pytest.approx(10.0, rel=1e-5)


# ---------------------------------------------------------------------------
# on_ground heuristic
# ---------------------------------------------------------------------------


class TestOnGroundHeuristic:
    def test_on_ground_when_agl_below_threshold(self) -> None:
        agl = _ON_GROUND_AGL_FT - 1.0
        pkt = _make_packet(_make_group(_ROW_GPS, 0.0, 0.0, 100.0, agl))
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.on_ground is True

    def test_airborne_when_agl_at_threshold(self) -> None:
        agl = _ON_GROUND_AGL_FT
        pkt = _make_packet(_make_group(_ROW_GPS, 0.0, 0.0, 100.0, agl))
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.on_ground is False

    def test_airborne_when_agl_above_threshold(self) -> None:
        agl = _ON_GROUND_AGL_FT + 1.0
        pkt = _make_packet(_make_group(_ROW_GPS, 0.0, 0.0, 1500.0, agl))
        s = parse_data_packet(pkt)
        assert s is not None
        assert s.on_ground is False


# ---------------------------------------------------------------------------
# XPlaneState defaults
# ---------------------------------------------------------------------------


class TestXPlaneStateDefaults:
    def test_all_numeric_defaults_are_zero(self) -> None:
        s = XPlaneState()
        assert s.latitude == 0.0
        assert s.longitude == 0.0
        assert s.altitude_msl_ft == 0.0
        assert s.altitude_agl_ft == 0.0
        assert s.vertical_speed_fpm == 0.0
        assert s.ground_speed_kts == 0.0

    def test_on_ground_default_is_false(self) -> None:
        assert XPlaneState().on_ground is False

    def test_timestamp_default_is_recent(self) -> None:
        before = time.time()
        s = XPlaneState()
        after = time.time()
        assert before <= s.timestamp <= after
