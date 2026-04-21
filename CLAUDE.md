# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main application
python3 main.py

# Test the NL→code engine in isolation
python3 nl_to_code/main.py
```

## Architecture

This is a smart home IoT automation system that bridges natural language commands with hardware control via WebSocket.

### Core Modules

- **main.py** — Entry point. Initializes the WebSocket client, registers tool functions (`gerer_led`, `read_memory`, `write_memory`), and handles routing of incoming messages.
- **WSClient.py** — WebSocket client (wraps `websocket-client`, extends PyQt5 `QObject` with fallback). Factory methods: `WSClient.dev()` (localhost:8765) and `WSClient.prod()` (192.168.10.127:9000).
- **Message.py** — Protocol layer defining message types (`ENVOI_*`, `RECEPTION_*`, `ADMIN_*`) and sensor IDs (`LIGHT`, `BUTTON`, `TEMPERATURE`, `RFID`, `LED`, etc.). JSON serialization via `from_json()` / `to_json()`.
- **Context.py** — Environment config (dev vs. prod WebSocket URLs).
- **nl_to_code/nl_to_code.py** — Two-stage LLM pipeline: (1) classify user input to a capability using `main.md`, (2) load capability-specific `.md` prompt and generate a JSON tool call. Calls llama.cpp at `http://localhost:8080/v1/chat/completions`. Configurable via env vars: `LLAMA_BASE_URL`, `LLAMA_API_KEY`, `LLAMA_MODEL`, `LLAMA_STREAM`.

### NL→Code Pipeline

1. User message → `execute_code_from()` in `main.py`
2. `nl_to_code.py` calls LLM with `main.md` to classify into a capability (`gerer_led`, `read_memory`, `write_memory`, `compter`, `autre`)
3. Loads the matching `.md` prompt from `nl_to_code/`
4. Calls LLM again → returns `{tool_name, arguments}` JSON
5. Executes the tool via dynamic dispatch

### Memory System

Persistent memory lives in `nl_to_code/current_state_memory.md`, a markdown file with `#CATEGORY:` section headers. Tools `read_memory` and `write_memory` in `main.py` read and append to this file.

### Message Flow

ESP32 sends sensor data → `WSClient.on_message()` → `main.py` handler → writes to memory / broadcasts temperature string / triggers NL processing for user commands.
