from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Waypoint:
    type: int   # 1=airport, 2=NDB, 3=VOR, 11=fix, 28=lat/lon
    ident: str
    via: str    # ADEP, ADES, DRCT, or SID/STAR name
    alt_ft: float
    lat: float
    lon: float


@dataclass
class FlightPlan:
    departure: str = ""
    arrival: str = ""
    dep_runway: str = ""
    arr_runway: str = ""
    sid: str = ""
    star: str = ""
    approach: str = ""
    cruise_fl: int = 0
    cycle: str = ""
    waypoints: list[Waypoint] = field(default_factory=list)


def parse(path: str | Path) -> FlightPlan:
    """Parse an X-Plane 12 .fms file and return a FlightPlan."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = [line.rstrip("\r\n") for line in text.splitlines()]
    return _parse_lines(lines)


def _parse_lines(lines: list[str]) -> FlightPlan:
    fp = FlightPlan()
    if not lines:
        return fp

    version = 0
    for line in lines[:4]:
        m = re.match(r"^(\d+)\s+[Vv]ersion", line.strip())
        if m:
            version = int(m.group(1))
            break

    if version >= 1100:
        _parse_v1100(lines, fp)
    else:
        _parse_v3(lines, fp)

    alts = [w.alt_ft for w in fp.waypoints if w.alt_ft > 0]
    if alts:
        fp.cruise_fl = int(max(alts) / 100)

    return fp


def _parse_v1100(lines: list[str], fp: FlightPlan) -> None:
    waypoints_started = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("CYCLE "):
            fp.cycle = line[6:].strip()
        elif line.startswith("ADEP "):
            fp.departure = line[5:].strip()
        elif line.startswith("DEPRWY "):
            fp.dep_runway = line[7:].strip().removeprefix("RW")
        elif line.startswith("SID "):
            fp.sid = line[4:].strip()
        elif line.startswith("ADES "):
            fp.arrival = line[5:].strip()
        elif line.startswith("DESRWY "):
            fp.arr_runway = line[7:].strip().removeprefix("RW")
        elif line.startswith("STAR "):
            fp.star = line[5:].strip()
        elif line.startswith("APP "):
            fp.approach = line[4:].strip()
        elif line.startswith("NUMENR "):
            waypoints_started = True
        elif waypoints_started:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    fp.waypoints.append(Waypoint(
                        type=int(parts[0]),
                        ident=parts[1],
                        via=parts[2],
                        alt_ft=float(parts[3]),
                        lat=float(parts[4]),
                        lon=float(parts[5]),
                    ))
                except (ValueError, IndexError):
                    pass


def _parse_v3(lines: list[str], fp: FlightPlan) -> None:
    """Parse older X-Plane FMS format (version 3/11)."""
    in_data = False
    for line in lines:
        line = line.strip()
        if re.match(r"^\d+\s+[Vv]ersion", line):
            in_data = True
            continue
        if not in_data or not line or line in ("I", "A"):
            continue
        parts = line.split()
        if parts and parts[0].isdigit() and len(parts) >= 5:
            try:
                fp.waypoints.append(Waypoint(
                    type=int(parts[0]),
                    ident=parts[1],
                    via="DRCT",
                    alt_ft=float(parts[2]),
                    lat=float(parts[3]),
                    lon=float(parts[4]),
                ))
            except (ValueError, IndexError):
                pass

    airports = [w for w in fp.waypoints if w.type == 1]
    if airports:
        fp.departure = airports[0].ident
    if len(airports) >= 2:
        fp.arrival = airports[-1].ident
