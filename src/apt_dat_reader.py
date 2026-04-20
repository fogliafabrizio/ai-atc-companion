from __future__ import annotations

from pathlib import Path

_COM_ROW_CODES: dict[int, str] = {
    50: "atis",
    52: "delivery",
    53: "ground",
    54: "tower",
    55: "approach",
    56: "departure",
}


def get_apt_dat_path(xplane_root: str | Path) -> Path:
    return (
        Path(xplane_root)
        / "Resources"
        / "default scenery"
        / "default apt dat"
        / "Earth nav data"
        / "apt.dat"
    )


def get_frequencies(apt_dat_path: str | Path, icao: str) -> dict[float, str]:
    """Stream-parse apt.dat; return {freq_mhz: role} for the given ICAO."""
    icao = icao.upper()
    result: dict[float, str] = {}
    in_airport = False
    with open(apt_dat_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if not parts or not parts[0].isdigit():
                continue
            code = int(parts[0])
            if code == 1:
                if in_airport:
                    break
                if len(parts) >= 5 and parts[4] == icao:
                    in_airport = True
            elif in_airport and code in _COM_ROW_CODES:
                result[int(parts[1]) / 100.0] = _COM_ROW_CODES[code]
    return result
