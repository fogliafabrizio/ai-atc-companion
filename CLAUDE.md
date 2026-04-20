# AI ATC Companion

## Project description

Standalone application (Windows/macOS) that runs alongside X-Plane 12 during IFR flight, simulating a complete and realistic ATC service through artificial intelligence. The pilot communicates by voice as on a real radio frequency. Each ATC role (Delivery, Ground, Tower, Departure, Approach) is handled by a dedicated Claude agent with ICAO phraseology, knowledge of airport procedures and memory of the current session.

**This project is also a learning path for Claude Code**: skills, hooks and MCP server are introduced progressively, milestone by milestone.

---

## Tech stack

| Component        | Technology                                            |
| ---------------- | ----------------------------------------------------- |
| Language         | Python 3.11+                                          |
| Simulator        | X-Plane 12 — native UDP protocol                      |
| STT              | faster-whisper (local, no internet)                   |
| AI / ATC         | Claude API — claude-sonnet, one agent per controller  |
| TTS              | OpenAI TTS with VHF audio filter                      |
| Navigation data  | X-Plane 12 CIFP folder (ARINC 424)                    |
| Flight plan      | `.fms` file exported from X-Plane 12                  |
| Configuration    | YAML + environment variables (`.env`)                 |

---

## Development commands

```bash
# Environment setup
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application (to be implemented)
python src/main.py

# Run tests
python -m pytest tests/
```

---

## Project structure

```
ai-atc-companion/
├── .claude/
│   ├── settings.json          # Claude Code configuration
│   └── hooks/
│       ├── pre_tool_use.py    # injects UDP state into context before each ATC reply
│       └── post_tool_use.py   # updates Session Manager after each ATC reply
│
├── skills/
│   ├── controller_prompt.md   # generates the system prompt for each ATC controller
│   ├── fms_parser.md          # reads and interprets X-Plane 12 .fms files
│   └── cifp_parser.md         # extracts SID/STAR from ARINC 424 files
│
├── mcp_server/
│   ├── server.py              # MCP server entry point
│   ├── tools/
│   │   ├── airport.py         # tool: get_airport_procedures(icao)
│   │   ├── session.py         # tool: get_session_state / set_session_state
│   │   └── flightplan.py      # tool: get_flight_plan()
│   └── requirements.txt
│
├── src/
│   ├── main.py                # application entry point
│   ├── udp_listener.py        # reads datarefs from X-Plane 12 via UDP
│   ├── session_manager.py     # global session state (squawk, taxi route, flight phase)
│   ├── controller_router.py   # routes transmissions to the correct controller
│   ├── audio_pipeline.py      # PTT → Whisper → Claude API → TTS → output
│   ├── controllers/           # one module per ATC role (delivery, ground, tower, …)
│   ├── cifp_parser.py         # ARINC 424 parser for SID/STAR
│   └── fms_reader.py          # .fms file reader
│
├── config/
│   ├── airports/              # airport data loaded at runtime
│   └── settings.yaml          # X-Plane path, PTT config, preferences
│
├── tests/
│   ├── test_udp_listener.py
│   ├── test_cifp_parser.py
│   ├── test_fms_reader.py
│   └── fixtures/              # sample .fms and CIFP files for tests
│
├── docs/
│   └── architecture.md        # architectural notes and design decisions
│
├── .env.example               # environment variables template
├── .gitignore
├── requirements.txt
└── CLAUDE.md                  # this file
```

---

## Architecture — main components

### UDP Listener

Reads X-Plane 12 datarefs in real time (GPS position, altitude, vertical speed, on-ground/in-flight state, active runway). Updates internal state every cycle and triggers controller changes during critical phases (e.g. TOD for descent start).

### Session Manager

Maintains the global session state: current flight phase, active controller, received clearances, assigned taxi route, transponder squawk, QNH. Serializes state as JSON and injects it into the active controller's prompt.

### Controller Router

Routes every pilot transmission to the correct controller based on the selected frequency and the flight phase. Each controller is a Claude agent with a dedicated system prompt.

### Audio Pipeline

Configurable PTT → faster-whisper (local transcription) → Claude API → OpenAI TTS → VHF filter → headphones output. Target latency: under 2 seconds.

### ATC Controllers

| Controller         | Typical frequency | Responsibilities                          |
| ------------------ | ----------------- | ----------------------------------------- |
| Clearance Delivery | 121.8 MHz         | IFR clearance, SID, squawk, QNH           |
| Ground             | 121.9 MHz         | Taxi route, holding point                 |
| Tower              | 118.7 MHz         | Takeoff, landing, runway traffic          |
| Departure          | 125.9 MHz         | SID climb management, vectors             |
| Approach           | 119.2 MHz         | STAR, approach, ILS, handoff              |

---

## Implementation roadmap

Strategy: **thin vertical slice first** — build a minimal end-to-end loop (UDP → PTT → Whisper → mock controller → TTS → headphones) before growing breadth. UI is CLI-only for v1.

Each milestone is one `feat/YYYYMMDD-<slug>` branch. Mark each task `[x]` when merged to `master` with all tests passing. A milestone is **DONE** only when all its checkboxes are checked.

### Current status (2026-04-20)

Overall completion: **~20%** — M1 complete, full audio pipeline functional.

---

### M1 — Thin vertical slice (MVP pipeline)  ✅ done

**Goal**: speak into the mic → hear a mock controller reply through headphones, while UDP state streams in the background. Validates the entire audio loop before any real ATC logic.

- [x] Add `sounddevice`, `pynput` (or `keyboard`), `numpy` to `requirements.txt`
- [x] Extend `config/settings.yaml` with `ptt_key`, `input_device`, `output_device`, `whisper_model_size`
- [x] `src/audio_pipeline.py` — PTT handler, mic capture, faster-whisper transcription, OpenAI TTS, playback
- [x] `src/session_manager.py` — `SessionManager` thread-safe store; polls `UDPListener.get_state()` at 2 Hz; holds `Transmission` log
- [x] `src/controller_router.py` — skeleton with a single `MockController` returning hardcoded replies
- [x] `src/main.py` — entry point: load config, start UDP listener, start session manager, register PTT, run event loop
- [x] `tests/test_session_manager.py` — state update + transmission log
- [x] `tests/test_controller_router.py` — mock controller routing by frequency
- [x] Manual verification against X-Plane 12: PTT → mock reply audible

---

### M2 — First real controller: Clearance Delivery  ✅ done

- [x] `skills/controller_prompt.md` — template for system prompt generation (role, ICAO, runway, METAR, session state)
- [x] `src/controllers/delivery.py` — Claude API call with `claude-sonnet`, builds prompt from skill + session
- [x] Update `src/controller_router.py` — route by frequency; `MockController` stays as fallback
- [x] CLI flag or config to toggle mock vs. real controller
- [x] `tests/test_delivery_controller.py` — assert response shape; record/replay if needed
- [ ] End-to-end: request IFR clearance, verify coherent SID / squawk / QNH

---

### M3 — Flight plan & navigation data  ⬜ not started

- [ ] `src/fms_reader.py` + `skills/fms_parser.md` — parse `.fms` → departure/arrival/route/aircraft/cruise FL
- [ ] `src/cifp_parser.py` + `skills/cifp_parser.md` — parse ARINC 424 SID/STAR for a given ICAO
- [ ] Sample `.fms` and CIFP fixtures in `tests/fixtures/`
- [ ] `tests/test_fms_reader.py`, `tests/test_cifp_parser.py`
- [ ] Session manager loads active flight plan at startup; controller prompts include it

---

### M4 — Remaining controllers + phase-driven routing  ⬜ not started

- [ ] `src/controllers/ground.py`
- [ ] `src/controllers/tower.py`
- [ ] `src/controllers/departure.py`
- [ ] `src/controllers/approach.py`
- [ ] Phase inference in `controller_router.py` from UDP state (on_ground + GS + AGL → taxi/takeoff/climb/cruise/descent/approach)
- [ ] Proactive handoff triggers (TOD detection, runway-in-sight cue)
- [ ] Smoke test per controller with canned session state

---

### M5 — Hooks + session persistence  ⬜ not started

- [ ] `.claude/hooks/pre_tool_use.py` — inject latest UDP state + session snapshot before each Claude call
- [ ] `.claude/hooks/post_tool_use.py` — extract squawk/clearance from ATC replies and update `SessionManager`
- [ ] Hook configuration in `.claude/settings.json`
- [ ] Session log persisted to disk (JSON lines) for replay/debug

---

### M6 — MCP server  ⬜ not started

- [ ] `mcp_server/server.py` — entry point
- [ ] `mcp_server/tools/airport.py` — `get_airport_procedures(icao)` wraps CIFP parser
- [ ] `mcp_server/tools/session.py` — `get_session_state()`, `update_session_state(patch)`
- [ ] `mcp_server/tools/flightplan.py` — `get_flight_plan()`
- [ ] `log_transmission(role, text, timestamp)` — structured session log tool
- [ ] Wire MCP server into the main app so controllers can call its tools

---

### M7 — Audio polish & CLI UX  ⬜ not started

- [ ] VHF audio filter in `audio_pipeline.py` (band-pass 300–3400 Hz + light distortion/compression via `scipy.signal`)
- [ ] Rich CLI output (via `rich`): current frequency, controller, last transmission, session state
- [ ] Persistent PTT configuration
- [ ] Audio device selection wizard on first run

---

### M8 — Minimal GUI (optional)  ⬜ deferred

Only if CLI UX proves insufficient after real flights. Likely `PyQt6`.

- [ ] Frequency selector
- [ ] Rolling transcription panel
- [ ] Session state panel
- [ ] Active controller indicator

---

## Skills Claude Code (developed alongside milestones)

- **`skills/fms_parser.md`** (M3) — how to read an X-Plane 12 `.fms` file and extract: departure/arrival airport, route, aircraft, cruise FL
- **`skills/controller_prompt.md`** (M2) — how to generate the system prompt for an ATC controller given: role, ICAO airport, active runway, weather, session state
- **`skills/cifp_parser.md`** (M3) — how to extract SID/STAR procedures from an ARINC 424 file in the X-Plane CIFP folder

---

## Hooks Claude Code (M5)

- **`pre_tool_use.py`** — before each ATC reply, automatically injects updated UDP state (altitude, speed, current flight phase)
- **`post_tool_use.py`** — after each ATC reply, updates the Session Manager with information exchanged (assigned squawk, received clearances)

---

## MCP Server (M6)

The MCP server exposes tools that Claude can call during the session:

- `get_airport_procedures(icao)` — SID/STAR from the CIFP parser
- `get_session_state()` / `update_session_state(patch)` — current state
- `get_flight_plan()` — data from the loaded `.fms`
- `log_transmission(role, text, timestamp)` — structured session log

---

## Required environment variables

See `.env.example`. Never commit the `.env` file.

```
ANTHROPIC_API_KEY=       # Anthropic API key
OPENAI_API_KEY=          # OpenAI API key (TTS)
XPLANE_PATH=             # X-Plane 12 folder path (for CIFP and .fms)
```

---

## Code conventions

- Language: Python 3.11+, typing with `typing` / `dataclasses`
- Formatting: `black` + `isort`
- Tests: `pytest`, fixtures in `tests/fixtures/`
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Branches: `feat/<unique-id>` (e.g. `feat/20260419-udp-listener`) — always work on a feature branch, never directly on `master`
- Always use `python`, never `python3`
- After each commit on a `feat/` branch:
  1. Run the tests (`python -m pytest tests/`) — merging to `master` is allowed only if all tests pass
  2. Ask whether to merge to `master`
  3. If yes: merge, push `master`, then immediately create a new `feat/<unique-id>` branch for the next work
  4. If no: push the current feature branch
