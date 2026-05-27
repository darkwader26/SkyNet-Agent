# SkyNet Agent

> **A next-generation AI agent — tool generation, self-improvement, autonomous background mode, multi-model routing.**

## What Makes It Different

| Feature | What It Does |
|---------|-------------|
| **🧠 Tool Generation** | Writes and registers new tools at runtime — infinite expansion |
| **🔄 Self-Improvement** | Reads its own system prompt, learns from mistakes, rewrites itself |
| **🏃 Autonomous Mode** | Background daemon that monitors and acts without being asked |
| **🎯 Multi-Model Router** | Routes tasks to the best model for each job |
| **🔧 Persistent Memory** | SQLite + FTS5 for session search + experience replay |

## Project Structure

```
SkyNet-Agent/
├── loop.py          # Core conversation loop
├── registry.py      # Tool registry with dynamic reload
├── memory.py        # SQLite memory store
├── router.py        # Multi-model provider router
├── daemon.py        # Background autonomous loop
├── improv.py        # Self-improvement engine
├── tools/           # Auto-discovered tool implementations
├── config.py        # Configuration
├── system_prompt.md # Agent identity (self-modifying)
└── requirements.txt
```

## Architecture

```
Orchestrator LLM (CEO)
├── Coder Agent — generates code
├── Research Agent — searches & synthesizes
├── Memory Agent — stores/retrieves
├── Background Loop — daemon for proactive tasks
└── Self-Improvement Engine — rewrites prompts & tools
```

## Quick Start

```bash
pip install -r requirements.txt
python loop.py
```

## License

MIT
