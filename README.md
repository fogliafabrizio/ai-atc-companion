# AI ATC Companion

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

## Configuration

Runtime settings live in `config/settings.yaml`. Secrets (API keys, X-Plane path) live in `.env`.

### X-Plane UDP port

`config/settings.yaml` controls the UDP port where the listener expects X-Plane 12 DATA packets:

```yaml
udp:
  port: 49100
```

X-Plane 12 itself binds ports `49000`, `49001` and a few others in the 49000-range for plugin and control traffic. **Do not reuse them** for Data Output — pick a port well outside (the default `49100` is a safe choice).

Configure the matching destination in X-Plane:

1. *Settings → Network → Data Output*
2. Tick "Send network data output" and set IP to `127.0.0.1`, Port to match `config/settings.yaml`
3. In the data list, enable the "Network via UDP" checkbox for rows **3** (Speeds), **4** (Mach, VVI, g-load), **20** (Lat/Lon/Alt)

Override the port ad-hoc from the command line without editing the YAML:

```bash
python src/udp_listener.py 49200
```

## Whisper model

The STT model is configured in `config/settings.yaml`:

```yaml
audio:
  whisper_model_size: "small"
```

| Model | Size | CPU latency | Notes |
|-------|------|-------------|-------|
| `base` | 74 MB | ~1 s | Low accuracy, fast |
| `small` | 244 MB | ~2 s | Good accuracy, recommended |
| `medium` | 769 MB | 3–6 s | Very good accuracy, GPU recommended |

The model is downloaded from HuggingFace on first run. `small` is the recommended default — noticeably more accurate than `base` while keeping latency within the 2-second target on CPU.

## Tests

```bash
python3 -m pytest tests/
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for architectural notes and design decisions.
