# AI ATC Companion

## Descrizione del progetto

Applicazione standalone (Windows/macOS) che affianca X-Plane 12 durante il volo IFR, simulando un servizio ATC completo e realistico tramite intelligenza artificiale. Il pilota comunica via voce come su una frequenza radio reale. Ogni ruolo ATC (Delivery, Ground, Tower, Departure, Approach) è gestito da un agente Claude dedicato con fraseologia ICAO, conoscenza delle procedure dell'aeroporto e memoria della sessione corrente.

**Questo progetto è anche un percorso di apprendimento su Claude Code**: skills, hooks e MCP server vengono introdotti progressivamente milestone per milestone.

---

## Stack tecnologico

| Componente       | Tecnologia                                           |
| ---------------- | ---------------------------------------------------- |
| Linguaggio       | Python 3.11+                                         |
| Simulatore       | X-Plane 12 — protocollo UDP nativo                   |
| STT              | faster-whisper (locale, no internet)                 |
| AI / ATC         | Claude API — claude-sonnet, un agente per controller |
| TTS              | OpenAI TTS con filtro audio VHF                      |
| Dati navigazione | CIFP folder di X-Plane 12 (ARINC 424)                |
| Piano di volo    | File .fms esportato da X-Plane 12                    |
| Configurazione   | YAML + variabili d'ambiente (.env)                   |

---

## Comandi di sviluppo

```bash
# Setup ambiente
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# Installare dipendenze
pip install -r requirements.txt

# Avviare l'applicazione (da implementare)
python src/main.py

# Eseguire i test
python -m pytest tests/
```

---

## Struttura del progetto

```
ai-atc-companion/
├── .claude/
│   ├── settings.json          # configurazione Claude Code
│   └── hooks/
│       ├── pre_tool_use.py    # inietta stato UDP nel contesto prima di ogni risposta ATC
│       └── post_tool_use.py   # aggiorna Session Manager dopo ogni risposta ATC
│
├── skills/
│   ├── controller_prompt.md   # genera system prompt per ogni controller ATC
│   ├── fms_parser.md          # legge e interpreta file .fms di X-Plane 12
│   └── cifp_parser.md         # estrae SID/STAR da file ARINC 424
│
├── mcp_server/
│   ├── server.py              # entry point MCP server
│   ├── tools/
│   │   ├── airport.py         # tool: get_airport_procedures(icao)
│   │   ├── session.py         # tool: get_session_state / set_session_state
│   │   └── flightplan.py      # tool: get_flight_plan()
│   └── requirements.txt
│
├── src/
│   ├── main.py                # entry point applicazione
│   ├── udp_listener.py        # legge datarefs da X-Plane 12 via UDP
│   ├── session_manager.py     # stato globale sessione (squawk, taxi route, fase volo)
│   ├── controller_router.py   # instrada le trasmissioni al controller corretto
│   ├── audio_pipeline.py      # PTT → Whisper → Claude API → TTS → output
│   ├── cifp_parser.py         # parser ARINC 424 per SID/STAR
│   └── fms_reader.py          # lettore file .fms
│
├── config/
│   ├── airports/              # dati aeroporto caricati a runtime
│   └── settings.yaml          # path X-Plane, configurazione PTT, preferenze
│
├── tests/
│   ├── test_udp_listener.py
│   ├── test_cifp_parser.py
│   ├── test_fms_reader.py
│   └── fixtures/              # file .fms e CIFP di esempio per i test
│
├── docs/
│   └── architecture.md        # note architetturali e decisioni di progetto
│
├── .env.example               # template variabili d'ambiente
├── .gitignore
├── requirements.txt
└── CLAUDE.md                  # questo file
```

---

## Architettura — componenti principali

### UDP Listener

Legge in tempo reale i datarefs di X-Plane 12 (posizione GPS, quota, velocità verticale, stato a terra/in volo, pista in uso). Aggiorna lo stato interno a ogni ciclo e triggera il cambio di controller nelle fasi critiche (es. TOD per inizio discesa).

### Session Manager

Mantiene lo stato globale della sessione: fase del volo corrente, controller attivo, clearance ricevute, taxi route assegnato, transponder squawk, QNH. Serializza lo stato come JSON e lo inietta nel prompt del controller attivo.

### Controller Router

Instrada ogni trasmissione del pilota al controller corretto in base alla frequenza selezionata e alla fase del volo. Ogni controller è un agente Claude con system prompt dedicato.

### Audio Pipeline

PTT configurabile → faster-whisper (trascrizione locale) → Claude API → OpenAI TTS → filtro VHF → output cuffie. Latenza target: sotto i 2 secondi.

### Controller ATC

| Controller         | Frequenza tipo | Responsabilità                       |
| ------------------ | -------------- | ------------------------------------ |
| Clearance Delivery | 121.8 MHz      | Clearance IFR, SID, squawk, QNH      |
| Ground             | 121.9 MHz      | Taxi route, holding point            |
| Tower              | 118.7 MHz      | Decollo, atterraggio, traffico pista |
| Departure          | 125.9 MHz      | Gestione salita SID, vettoramenti    |
| Approach           | 119.2 MHz      | STAR, avvicinamento, ILS, handoff    |

---

## Skills Claude Code (in sviluppo progressivo)

- **`skills/fms_parser.md`** — come leggere un file .fms di X-Plane 12 ed estrarre: aeroporto di partenza/arrivo, rotta, aeromobile, FL crociera
- **`skills/controller_prompt.md`** — come generare il system prompt per un controller ATC dato: ruolo, aeroporto ICAO, pista in uso, meteo, stato sessione
- **`skills/cifp_parser.md`** — come estrarre procedure SID/STAR da un file ARINC 424 della CIFP folder di X-Plane

---

## Hooks Claude Code (in sviluppo progressivo)

- **`pre_tool_use.py`** — prima di ogni risposta ATC, inietta automaticamente lo stato UDP aggiornato (quota, velocità, fase del volo corrente)
- **`post_tool_use.py`** — dopo ogni risposta ATC, aggiorna il Session Manager con le informazioni scambiate (squawk assegnato, autorizzazioni ricevute)

---

## MCP Server (fase 3)

Il MCP server espone strumenti che Claude può chiamare durante la sessione:

- `get_airport_procedures(icao)` — SID/STAR dal CIFP parser
- `get_session_state()` / `update_session_state(patch)` — stato corrente
- `get_flight_plan()` — dati del .fms caricato
- `log_transmission(role, text, timestamp)` — log strutturato della sessione

---

## Milestone di sviluppo

### Fase 1 — Prototipo core (Skills)

- UDP listener funzionante con dati da X-Plane 12
- Lettura file .fms → skill `fms_parser`
- Mock controller (risposta hardcoded) per testare la pipeline audio
- Primo controller reale: Clearance Delivery

### Fase 2 — Controller completi (Hooks)

- Tutti e 5 i controller con system prompt dedicati
- Session Manager con stato condiviso
- Hook pre/post per cambio controller automatico via UDP
- Trigger proattivi: TOD, handoff di frequenza

### Fase 3 — UI e MCP

- Interfaccia grafica: frequenza attiva, trascrizione, log sessione
- MCP server per database aeroporti e log strutturato
- Filtro audio VHF
- Configurazione PTT persistente

---

## Variabili d'ambiente richieste

Vedi `.env.example`. Non committare mai il file `.env`.

```
ANTHROPIC_API_KEY=       # API key Anthropic
OPENAI_API_KEY=          # API key OpenAI (TTS)
XPLANE_PATH=             # path cartella X-Plane 12 (per CIFP e .fms)
```

---

## Convenzioni di codice

- Linguaggio: Python 3.11+, tipizzazione con `typing` / `dataclasses`
- Formattazione: `black` + `isort`
- Test: `pytest`, fixture in `tests/fixtures/`
- Commit: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Branch: `feat/<id-univoco>` (es. `feat/20260419-udp-listener`) — sempre lavorare su un ramo di feature, mai direttamente su `master`
- Usare sempre `python`, mai `python3`
- Dopo ogni commit su un ramo `feat/`:
  1. Eseguire i test (`python -m pytest tests/`) — il merge su `master` è consentito solo se tutti i test passano
  2. Chiedere se si vuole fare il merge su `master`
  3. Se sì: merge, push di `master`, poi creare subito un nuovo ramo `feat/<id-univoco>` per il lavoro successivo
  4. Se no: push del ramo di feature corrente
