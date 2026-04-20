# FMS Parser — X-Plane 12 `.fms` file format

## Format overview

X-Plane 12 exports flight plans in `.fms` format (version 1100). The file is plain text UTF-8 with a structured header followed by a fixed-width waypoint list.

## Header structure

```
I
1100 Version
CYCLE YYMM
ADEP  <departure ICAO>
DEPRWY RW<runway>          (optional)
SID   <SID name>           (optional)
SIDTRANS --                (optional)
ADES  <arrival ICAO>
DESRWY RW<runway>          (optional)
STAR  <STAR name>          (optional)
STARTRANS --               (optional)
APP   <approach>           (optional)
NUMENR <count>
```

## Waypoint record format

Each waypoint is a space-separated line with 6 fields:

```
<type> <ident> <via> <alt_ft> <lat> <lon>
```

| Field    | Values                                              |
| -------- | --------------------------------------------------- |
| `type`   | 1=airport, 2=NDB, 3=VOR, 11=named fix, 28=lat/lon  |
| `ident`  | ICAO or fix name (e.g. `LIML`, `OPTO`)              |
| `via`    | `ADEP`, `ADES`, `DRCT`, or procedure name           |
| `alt_ft` | Altitude in feet (0 for airports)                   |
| `lat`    | Decimal degrees, positive = North                   |
| `lon`    | Decimal degrees, positive = East                    |

## Example (LIML → LIRF)

```
I
1100 Version
CYCLE 2312
ADEP LIML
DEPRWY RW36
SID OPTO1E
SIDTRANS --
ADES LIRF
DESRWY RW16L
STAR GINA2A
APP I16L
NUMENR 8
1 LIML ADEP 0.000000 45.445083 9.276750
11 OPTO DRCT 9000.000000 45.557222 9.492222
11 MARIO DRCT 14000.000000 45.736667 9.746944
11 SOGMI DRCT 24000.000000 44.960000 10.700000
11 NUVLO DRCT 20000.000000 43.993333 11.630000
11 GINA DRCT 18000.000000 42.980000 12.026667
11 MAREN DRCT 8000.000000 41.906111 12.340833
1 LIRF ADES 0.000000 41.800322 12.238862
```

## Parsing with src/fms_reader.py

```python
from src.fms_reader import parse

fp = parse("path/to/plan.fms")
print(fp.departure)   # 'LIML'
print(fp.arrival)     # 'LIRF'
print(fp.sid)         # 'OPTO1E'
print(fp.dep_runway)  # '36'  (RW prefix stripped)
print(fp.arr_runway)  # '16L'
print(fp.cruise_fl)   # 240  (max waypoint altitude / 100)
print([w.ident for w in fp.waypoints])  # ['LIML', 'OPTO', ..., 'LIRF']
```

## Derived fields

- `cruise_fl`: computed as `int(max_altitude_ft / 100)` across all waypoints
- `dep_runway` / `arr_runway`: the `RW` prefix from `DEPRWY`/`DESRWY` is stripped automatically

## Notes

- SIDTRANS and STARTRANS are parsed and ignored (they carry the transition name, not the procedure name)
- Older version-3 format is supported in fallback mode: extracts waypoints and infers departure/arrival from the first and last type-1 entries
- X-Plane 12 always writes version 1100; use that as the primary format
