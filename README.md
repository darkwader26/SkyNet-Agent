# SkyNet Agent

> An autonomous AI agent with persistent memory, self-improvement, tool generation, and multi-model routing. For when one model isn't enough and you want an agent that gets smarter every time you use it.

## Quick Start

```bash
# 1. Set your API key
cp .env.example .env
# Edit .env with your OPENAI_API_KEY or OPENROUTER_API_KEY

# 2. Install
pip install -r requirements.txt

# 3. Run
python main.py

# 4. Chat
> what's the latest news on AI?
> toolgen fetch stock prices from Yahoo Finance
> search_files "def main" path=. file_glob="*.py"
> /learn
```

## What Makes It Different

| Feature | What It Does |
|---------|-------------|
| **🧠 Self-Improvement** | Learns from failures using an LLM, extracts lessons, and appends them to its system prompt automatically |
| **🛠️ Tool Generation** | Type `toolgen <prompt>` and it writes, validates, and registers a new Python tool at runtime |
| **🌐 Web Search** | DuckDuckGo-based — no API key needed. Searches the web and fetches page content |
| **💻 Code Sandbox** | Executes Python and bash in isolated subprocesses to verify its own code |
| **📁 File System** | Read, write, search, and list files with grep integration |
| **🧠 Persistent Memory** | SQLite + FTS5 for session search, fact storage, and experience replay |
| **🎯 Smart Router** | LLM-based task classification routes reasoning to powerful models, simple lookups to fast ones. Auto-failover if a provider goes down |
| **⏰ Scheduling** | Create recurring jobs (`cron_create 'daily report' 'every day' 'summarize my projects'`) |
| **🔧 16+ Tools Built-in** | Search, fetch, execute, read, write, remember, schedule — all at launch |

## Architecture

```
main.py                      ← Entry point with CLI args
├── skynet/
│   ├── agent.py             ← Core conversation loop + slash commands
│   ├── config.py            ← Provider/model routing config
│   ├── registry.py          ← Dynamic tool registry with validation
│   ├── memory.py            ← SQLite + FTS5 memory system
│   ├── router.py            ← LLM-based task classifier + failover
│   ├── improv.py            ← Self-improvement engine
│   └── daemon.py            ← Background autonomous mode
├── tools/                   ← Auto-discovered tool modules
│   ├── web_search.py        ← DuckDuckGo search + fetch
│   ├── executor.py          ← Python/bash sandbox
│   ├── filesystem.py        ← read/write/search files
│   ├── memories.py          ← Memory read/write/delete
│   ├── cron.py              ← Scheduling tools
│   └── router_info.py       ← Router inspection
└── system_prompt.md         ← Agent identity & rules (self-modifying!)
```

## Self-Improvement

SkyNet learns from its mistakes. Here's how:

1. A tool call fails → the experience is logged to SQLite
2. A cheap LLM analyzes the failure and extracts a concrete lesson
3. The lesson is appended to `system_prompt.md` under `## 🧠 Learned Rules`
4. On the next turn, the agent reads the new rule and avoids the same mistake
5. Every 10+ rules, they get consolidated into a tighter set

```text
# Before: agent fails because it didn't check a path exists
> read_file("/nonexistent/file.txt")
Error: File not found

# After: system prompt automatically gains:
## 🧠 Learned Rules
- Before reading a file, always verify the path exists first
```

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
| `/route <q>` | Classify a task (which model?) |
| `/consolidate` | Consolidate learned rules |
| `/new` | Start a fresh session |
| `/help` | Show all commands |
| `toolgen <desc>` | Generate a new tool at runtime |

## CLI Options

```bash
python main.py --help

  -m, --model MODEL     Default model
  -r, --resume SESSION  Resume a session
  --no-improve          Disable self-improvement
  --yolo                Skip approval gates
  -q, --query TEXT      Single query mode
  --daemon              Enable background daemon
  --db PATH             Memory database path
  --prompt PATH         System prompt path
  --tools-dir PATH      Tools directory
```

## Requirements

- Python 3.10+
- An API key (OpenAI, OpenRouter, DeepSeek, Anthropic, or local Ollama)
- `curl` (for web search)

## License

MIT
