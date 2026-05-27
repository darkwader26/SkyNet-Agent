"""Central configuration — providers, model routing, agent settings.
Loads from .env with sane defaults.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, List

# ─── Model Router ───────────────────────────────────────────────────────

MODEL_ROUTER = {
    "reasoning":  os.getenv("MODEL_REASONING", "openai/gpt-4o"),
    "code":       os.getenv("MODEL_CODE", "openai/gpt-4o"),
    "creative":   os.getenv("MODEL_CREATIVE", "openai/gpt-4o"),
    "fast":       os.getenv("MODEL_FAST", "openai/gpt-4o-mini"),
    "local":      os.getenv("MODEL_LOCAL", "ollama/llama3"),
    "vision":     os.getenv("MODEL_VISION", "openai/gpt-4o"),
    "cheap":      os.getenv("MODEL_CHEAP", "openai/gpt-4o-mini"),
    "classifier": os.getenv("MODEL_CLASSIFIER", "openai/gpt-4o-mini"),
}

# ─── Providers ──────────────────────────────────────────────────────────
# (base_url, api_key_env, requires_litellm)

PROVIDERS: Dict[str, tuple] = {
    "openrouter": (
        "https://openrouter.ai/api/v1",
        os.getenv("OPENROUTER_API_KEY", ""),
        False,
    ),
    "openai": (
        "https://api.openai.com/v1",
        os.getenv("OPENAI_API_KEY", ""),
        False,
    ),
    "deepseek": (
        "https://api.deepseek.com/v1",
        os.getenv("DEEPSEEK_API_KEY", ""),
        False,
    ),
    "ollama": (
        "http://localhost:11434/v1",
        os.getenv("OLLAMA_API_KEY", "ollama"),
        False,
    ),
}

# ─── Agent Config ───────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    # Loop
    max_turns: int = 90
    max_tool_calls_per_turn: int = 20
    stream: bool = True

    # Paths
    system_prompt_path: str = "system_prompt.md"
    memory_db_path: str = "data/memory.db"
    tools_dir: str = "tools"
    data_dir: str = "data"

    # Session
    session_id: Optional[str] = None
    resume_session: bool = False

    # Self-improvement
    auto_improve: bool = True
    improvement_llm: str = "cheap"  # model tier to use for learning

    # Background daemon
    daemon_enabled: bool = False
    daemon_interval_sec: int = 60

    # Tool generation
    allow_tool_creation: bool = True
    toolgen_model: str = "code"

    # Safety
    approval_mode: str = "smart"  # "off" | "smart" | "all"
    approval_exempt: List[str] = field(default_factory=lambda: [
        "echo", "web_search", "read_file", "search_files",
        "list_tools", "router_status", "memory_search",
    ])

    # Logging
    log_file: Optional[str] = "data/skynet.log"
    log_level: str = "INFO"

    # Default model
    default_model: str = "openai/gpt-4o"


def load_config() -> AgentConfig:
    return AgentConfig()


def resolve_model(model_id: str) -> tuple:
    """Resolve 'provider/model' → (base_url, api_key, actual_model)."""
    if model_id.count("/") == 1 and not model_id.startswith("gpt"):
        provider, model_name = model_id.split("/", 1)
        if provider in PROVIDERS:
            url, key, _ = PROVIDERS[provider]
            return url, key, model_name
    return PROVIDERS["openai"][0], PROVIDERS["openai"][1], model_id
