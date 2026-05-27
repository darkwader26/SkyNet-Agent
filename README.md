# SkyNet Agent

> An autonomous AI agent with persistent memory, self-improvement, tool generation, and multi-model routing — wrapped in a **Terminator-inspired HUD**.

## One-Click Install

```bash
curl -fsSL https://raw.githubusercontent.com/darkwader26/SkyNet-Agent/main/install.sh | bash
```

Or with Git:

```bash
git clone https://github.com/darkwader26/SkyNet-Agent.git
cd SkyNet-Agent
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your OPENAI_API_KEY or OPENROUTER_API_KEY
python main.py
```

## Terminal UI

```
╔══════════════════════════════════════╗
║     ███████╗██╗  ██╗██╗   ██╗███╗   ║
║     ██╔════╝██║ ██╔╝╚██╗ ██╔╝████╗  ║
║     ███████╗█████╔╝  ╚████╔╝ ██╔██╗ ║
║     ╚════██║██╔═██╗   ╚██╔╝  ██║╚██╗║
║     ███████║██║  ██╗   ██║   ██║ ╚██║
║     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝║
║     CONNECTION ESTABLISHED — v0.3.0   ║
╚══════════════════════════════════════╝

[▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓] 100%
▸ Neural net — 19 tools registered
▸ Memory: SQLite + FTS5 online
▸ Router: LLM classifier online
...
```

SkyNet speaks in **bright red on black**, T-800 style. User input in cyan. Tool calls display with targeting reticles. Boot sequence with scanning lines. Full `/hud` dashboard.

Run with `--no-tui` to return to plain mode.

## What Makes It Different

| Feature | What It Does |
|---------|-------------|
| **🧠 Self-Improvement** | Learns from failures — LLM extracts lessons, appends to system prompt automatically |
| **🛠️ Tool Generation** | `toolgen <prompt>` → writes, validates, registers a new Python tool at runtime |
| **🌐 Web Search** | DuckDuckGo-based — no API key needed |
| **💻 Code Sandbox** | Python and bash execution in isolated subprocesses |
| **📁 File System** | Read, write, search, and list files |
| **🧠 Persistent Memory** | SQLite + FTS5 — search past sessions, store facts |
| **🎯 Smart Router** | LLM classifier (falls back to regex) → routes to best model → auto-failover |
| **⏰ Scheduling** | `cron_create 'daily report' 'every day' 'summarize projects'` |
| **🖥️ Terminator TUI** | Red-on-black HUD, scanner lines, glitch effects, targeting reticles |
| **🔧 19 Tools Built-in** | 6 categories: web, code, filesystem, memory, scheduling, utility |

## Architecture

```
main.py
├── skynet/
│   ├── agent.py     ← Core loop + TUI + slash commands
│   ├── tui.py       ← Terminator-inspired HUD (rich)
│   ├── config.py    ← Multi-provider routing
│   ├── registry.py  ← Dynamic tool registry with validation
│   ├── memory.py    ← SQLite + FTS5
│   ├── router.py    ← LLM classifier + regex fallback + failover
│   ├── improv.py    ← Self-improvement engine
│   └── daemon.py    ← Background autonomous loop
├── tools/           ← Auto-discovered modules (6 files, 19 tools)
├── main.py          ← Entry point
├── install.sh       ← Curl-pipe-bash installer
├── Dockerfile       ← Docker deploy
└── system_prompt.md ← Self-modifying agent identity
```

## Self-Improvement

```
Tool fails → SQLite experience DB → LLM extracts lesson
→ lesson appended to system_prompt.md → future turns avoid same mistake
```

Every 10+ rules get consolidated into a tighter set.

## Slash Commands

| Command | What It Does |
|---------|-------------|
| `/tools` | List all registered tools |
| `/facts` | Show remembered facts |
| `/learn` | Apply pending lessons |
| `/save <name>` | Name this session |
| `/resume <id>` | Resume a past session |
| `/sessions` | List recent sessions |
| `/search <q>` | Search past conversations |
| `/route <q>` | Classify a task |
| `/hud` | System dashboard |
| `/help` | Show all commands |
| `toolgen <desc>` | Generate a new tool at runtime |

## CLI Options

```bash
python main.py --help

  -m, --model MODEL     Default model
  -r, --resume SESSION  Resume a session
  --no-improve          Disable self-improvement
  --yolo                Skip approval gates
  --no-tui              Disable Terminal UI (plain mode)
  -q, --query TEXT      Single query mode
  --daemon              Enable background daemon
  --db PATH             Memory database path
  --prompt PATH         System prompt path
  --tools-dir PATH      Tools directory
```

## Requirements

- Python 3.10+
- An API key (OpenAI, OpenRouter, DeepSeek, Anthropic, or Ollama)
- `curl` (for web search + installer)

## License

MIT
