# CIFP Parser — ARINC 424 navigation data

## Format overview

X-Plane 12 stores navigation data in ARINC 424 format under:
```
<XPlane>/Resources/default data/CIFP/<ICAO>.dat
```
One file per airport. Each record is exactly 132 characters wide (fixed-width, no delimiters).

## Record structure (key fields, 0-indexed)

| Range    | Field                | Notes                              |
| -------- | -------------------- | ---------------------------------- |
| `[0]`    | Record type          | `S` = standard                     |
| `[1:4]`  | Area code            | `EUR`, `USA`, etc.                 |
| `[4]`    | Section code         | `P` = airport                      |
| `[5]`    | Subsection code      | `D` = SID, `E` = STAR, `F` = appr |
| `[6:10]` | Airport ICAO         | e.g. `LIML`                        |
| `[13:19]`| Procedure identifier | 6 chars, e.g. `OPTO1E`             |
| `[19:25]`| Transition identifier| 6 chars; `RW36  ` for runway legs  |
| `[26:29]`| Sequence number      | 3-digit, e.g. `010`                |
| `[29:34]`| Fix identifier       | 5 chars, e.g. `OPTO `, `RW36 `    |

Records that are not section `P` / subsection `D` or `E` are ignored.

## Procedure structure

Each SID or STAR has:
- A **common section** where the transition ID equals the procedure name
- One or more **runway/waypoint transitions** where the transition ID differs

Example for SID `OPTO1E` at `LIML`:
```
...OPTO1EOPTO1E 010LIML ...   ← common section, seq 010, airport start fix
...OPTO1EOPTO1E 020OPTO  ...   ← common section, seq 020, first waypoint
...OPTO1ERW36   010RW36  ...   ← runway 36 transition
...OPTO1ERW36   020OPTO  ...   ← runway 36 transition, waypoint
```

## Parsing with src/cifp_parser.py

```python
from src.cifp_parser import get_procedures, parse_airport

# Load by ICAO from X-Plane CIFP directory
procs = get_procedures("/path/to/XPlane/Resources/default data/CIFP", "LIML")

# Or parse a specific file directly
procs = parse_airport("/path/to/LIML.dat")

sids  = [p for p in procs if p.type == "SID"]
stars = [p for p in procs if p.type == "STAR"]

for sid in sids:
    print(sid.name, "runways:", sid.runways())
    # e.g. 'OPTO1E' runways: ['36']
```

## Key methods on Procedure

- `procedure.runways()` — list of runway IDs from `RW`-prefixed transitions (e.g. `['36', '18']`)
- `procedure.transitions` — all raw stripped transition identifiers
- `procedure.steps` — ordered list of `ProcedureStep(sequence, fix_ident, transition)`

## Typical usage in this project

```python
# Get SIDs applicable to active runway
runway = "36"
matching_sids = [
    p for p in procs
    if p.type == "SID" and runway in p.runways()
]
```

## Notes

- The CIFP directory path is configured in `settings.yaml` as `xplane_path`; the parser appends `Resources/default data/CIFP/<ICAO>.dat`
- Records shorter than 38 characters are silently skipped
- Approach records (subsection `F`) are not parsed — they are out of scope for the current milestone
