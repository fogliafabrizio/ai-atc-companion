from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProcedureStep:
    sequence: int
    fix_ident: str
    transition: str  # raw transition string from the record


@dataclass
class Procedure:
    name: str
    type: str     # 'SID' or 'STAR'
    airport: str
    transitions: list[str] = field(default_factory=list)   # raw stripped values, e.g. 'OPTO1E', 'RW36'
    steps: list[ProcedureStep] = field(default_factory=list)

    def runways(self) -> list[str]:
        """Runway IDs from runway-specific transitions (strips 'RW' prefix)."""
        return [t[2:] for t in self.transitions if t.startswith("RW")]


def parse_airport(path: str | Path) -> list[Procedure]:
    """Parse all SID and STAR procedures from an ARINC 424 CIFP file."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return _parse_lines(text.splitlines())


def get_procedures(cifp_dir: str | Path, icao: str) -> list[Procedure]:
    """Load procedures for a specific ICAO from the CIFP directory."""
    cifp_path = Path(cifp_dir) / f"{icao.upper()}.dat"
    if not cifp_path.exists():
        return []
    return parse_airport(cifp_path)


def _parse_lines(lines: list[str]) -> list[Procedure]:
    # ARINC 424 column positions (0-indexed):
    # [4]     section code     'P' = airport
    # [5]     subsection code  'D' = SID, 'E' = STAR
    # [6:10]  airport ICAO
    # [13:19] procedure identifier (6 chars)
    # [19:25] transition identifier (6 chars)
    # [25]    blank separator
    # [26:29] sequence number
    # [29:34] fix/waypoint identifier (5 chars)
    procedures: dict[tuple[str, str], Procedure] = {}

    for line in lines:
        if len(line) < 38:
            continue

        section = line[4]
        subsection = line[5]

        if section != "P" or subsection not in ("D", "E"):
            continue

        proc_type = "SID" if subsection == "D" else "STAR"
        airport = line[6:10].strip()
        proc_name = line[13:19].strip()
        transition = line[19:25].strip()

        if not proc_name or not airport:
            continue

        seq_str = line[26:29].strip()
        seq = int(seq_str) if seq_str.isdigit() else 0
        fix = line[29:34].strip()

        key = (proc_type, proc_name)
        if key not in procedures:
            procedures[key] = Procedure(name=proc_name, type=proc_type, airport=airport)

        proc = procedures[key]

        if transition and transition not in proc.transitions:
            proc.transitions.append(transition)

        if fix:
            proc.steps.append(ProcedureStep(sequence=seq, fix_ident=fix, transition=transition))

    return list(procedures.values())
