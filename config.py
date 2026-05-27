"""Configuration — provider abstraction, model routing, agent settings."""

import os
from dataclasses import dataclass, field
from typing import Optional

# ─── Model Router ───────────────────────────────────────────────────────

MODEL_ROUTER = {
    "reasoning": os.getenv("MODEL_REASONING", "anthropic/claude-sonnet-4-20250514"),
    "code": os.getenv("MODEL_CODE", "deepseek/deepseek-chat"),
    "creative": os.getenv("MODEL_CREATIVE", "mistral/mistral-large-latest"),
    "fast": os.getenv("MODEL_FAST", "openai/gpt-4o-mini"),
    "local": os.getenv("MODEL_LOCAL", "ollama/llama3"),
    "vision": os.getenv("MODEL_VISION", "openai/gpt-4o"),
    "cheap": os.getenv("MODEL_CHEAP", "deepseek/deepseek-chat"),
}

# ─── Providers ──────────────────────────────────────────────────────────

# Each provider is (base_url, api_key, model_prefix)
PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1", os.getenv("OPENROUTER_API_KEY", ""), ""),
    "openai": ("https://api.openai.com/v1", os.getenv("OPENAI_API_KEY", ""), ""),
    "anthropic": ("https://api.anthropic.com/v1", os.getenv("ANTHROPIC_API_KEY", ""), ""),
    "deepseek": ("https://api.deepseek.com/v1", os.getenv("DEEPSEEK_API_KEY", ""), ""),
    "ollama": ("http://localhost:11434/v1", os.getenv("OLLAMA_API_KEY", "ollama"), ""),
}

# ─── Agent Settings ─────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    max_turns: int = 90
    max_tool_calls_per_turn: int = 20
    system_prompt_path: str = "system_prompt.md"
    memory_db_path: str = "memory.db"
    tools_dir: str = "tools"
    
    # Self-improvement
    auto_improve: bool = True
    improvement_log_path: str = "improvements.jsonl"
    
    # Background daemon
    daemon_enabled: bool = False
    daemon_interval: int = 60  # seconds
    
    # Tool generation
    allow_tool_creation: bool = True


def load_config() -> AgentConfig:
    return AgentConfig()
