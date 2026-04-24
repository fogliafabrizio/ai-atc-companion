from __future__ import annotations

from pathlib import Path

# apt.dat ≤1100 row codes (frequency stored as Hz×100, divide by 100 for MHz)
_COM_ROW_CODES_V1: dict[int, str] = {
    50: "atis",
    52: "delivery",
    53: "ground",
    54: "tower",
    55: "approach",
    56: "departure",
}

# apt.dat 1200 row codes (frequency stored in kHz, divide by 1000 for MHz)
_COM_ROW_CODES_V2: dict[int, str] = {
    1050: "atis",
    1052: "delivery",
    1053: "ground",
    1054: "tower",
    1055: "approach",
    1056: "departure",
}

_ALL_COM_CODES: dict[int, tuple[str, float]] = {
    code: (role, 100.0) for code, role in _COM_ROW_CODES_V1.items()
} | {
    code: (role, 1000.0) for code, role in _COM_ROW_CODES_V2.items()
}


def get_apt_dat_path(xplane_root: str | Path) -> Path:
    root = Path(xplane_root)
    candidates = [
        root / "Resources" / "default scenery" / "default apt dat" / "Earth nav data" / "apt.dat",
        root / "Global Scenery" / "Global Airports" / "Earth nav data" / "apt.dat",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]  # let the caller surface the FileNotFoundError


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
            elif in_airport and code in _ALL_COM_CODES:
                role, divisor = _ALL_COM_CODES[code]
                result[int(parts[1]) / divisor] = role
    return result
