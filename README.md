# AI ATC Companion

Standalone desktop app (Windows/macOS) that simulates a full IFR ATC service alongside X-Plane 12. The pilot communicates via voice as on a real radio frequency. Each ATC role (Delivery, Ground, Tower, Departure, Approach) is handled by a dedicated Claude agent with ICAO phraseology, airport procedure knowledge, and session memory.

## Requirements

- Python 3.11+
- X-Plane 12
- Anthropic API key
- OpenAI API key (TTS)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API keys and X-Plane path
```

## Running

```bash
python3 src/main.py
```

## Tests

```bash
python3 -m pytest tests/
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for architectural notes and design decisions.
