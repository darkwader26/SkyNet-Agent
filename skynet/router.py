"""Smart multi-model router — LLM-based task classification with provider failover.

Routes each task to the best model, with automatic failover if a provider fails.
Uses a cheap model for classification, then routes to the best model for execution.
"""

import json
import re
import time
from typing import Optional, Dict, List, Tuple
from openai import OpenAI

from .config import MODEL_ROUTER, PROVIDERS, resolve_model


# ─── Provider management ────────────────────────────────────────────────

# Track provider health
_provider_health: Dict[str, dict] = {}


def _get_client_for_provider(provider: str) -> Tuple[Optional[OpenAI], Optional[str]]:
    """Get an OpenAI client for a provider. Returns (client, model) or (None, None)."""
    info = PROVIDERS.get(provider)
    if not info:
        return None, None
    base_url, api_key, _ = info
    if not api_key:
        return None, None
    try:
        return OpenAI(base_url=base_url, api_key=api_key, timeout=30), None
    except Exception:
        return None, None


def _get_client_for_model(model_id: str) -> Tuple[Optional[OpenAI], str]:
    """Resolve model string to (client, actual_model_name)."""
    if model_id.count("/") == 1 and not model_id.startswith(("gpt", "o1", "o3")):
        provider, model_name = model_id.split("/", 1)
        client, _ = _get_client_for_provider(provider)
        if client:
            return client, model_name
        # Fallback: try OpenAI directly
    base_url, api_key, _ = PROVIDERS.get("openai", ("", "", ""))
    if api_key:
        return OpenAI(base_url=base_url, api_key=api_key, timeout=30), model_id
    # No API key available — caller handles None
    return None, model_id


def _call_llm(messages: list, model_id: str, max_tokens: int = 500,
              temperature: float = 0.0) -> Optional[str]:
    """Call an LLM with automatic failover across providers."""
    errors = []

    # Primary attempt
    client, model = _get_client_for_model(model_id)
    if client:
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages,
                max_tokens=max_tokens, temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            errors.append(f"{model_id}: {e}")

    # Failover: try all other providers
    for provider, (url, api_key, _) in PROVIDERS.items():
        model_prefix = model_id.split("/")[0]
        if provider == model_prefix or not api_key:
            continue
        try:
            fallback_client = OpenAI(base_url=url, api_key=api_key, timeout=30)
            fallback_model = model_id.split("/")[-1] if "/" in model_id else model_id
            resp = fallback_client.chat.completions.create(
                model=fallback_model, messages=messages,
                max_tokens=max_tokens, temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            errors.append(f"{provider}: {e}")

    return None


# ─── Task Classification ────────────────────────────────────────────────

_CLASSIFICATION_CACHE = {}


def _regex_classify(prompt: str) -> str:
    """Regex-based classification fallback when LLM is unavailable."""
    p = prompt.lower().strip()

    # Very short queries or questions → fast
    if len(p) < 20 or p.startswith("what") or p.startswith("who") or p.startswith("when"):
        return "fast"

    # Code-related patterns
    if any(kw in p for kw in
           ("def ", "class ", "import ", "function", "return ", "async ",
            "lambda", "debug", "compile", "syntax", "type", "pytest",
            "refactor", "implement", "algorithm", "sort ")):
        return "code"

    # Tool actions
    if any(kw in p for kw in
           ("search", "find", "fetch", "read", "write", "list", "create",
            "delete", "save", "file", "tool", "execute", "run", "scan",
            "download", "upload", "schedule", "cron")):
        return "tool"

    # Creative
    if any(kw in p for kw in
           ("poem", "story", "write a ", "creative", "joke", "song",
            "compose", "generate a story", "haiku", "fiction")):
        return "creative"

    # Reasoning (default for complex)
    if any(kw in p for kw in
           ("why", "explain", "compare", "analyze", "evaluate",
            "difference between", "pros and cons", "how does")):
        return "reasoning"

    return "fast"


def classify_task(prompt: str) -> str:
    """Classify a task using a cheap LLM (not regex)."""
    # Check cache
    prompt_stub = prompt[:100]
    if prompt_stub in _CLASSIFICATION_CACHE:
        return _CLASSIFICATION_CACHE[prompt_stub]

    sys_msg = (
        "Classify the following user request into exactly one category.\n"
        "Categories:\n"
        "- code: writing, generating, or debugging code\n"
        "- reasoning: complex analysis, explanations, comparisons\n"
        "- creative: writing stories, poems, creative content\n"
        "- fast: simple factual questions, definitions, quick lookups\n"
        "- vision: anything involving images or visual content\n"
        "- tool: requests to use tools, access files, or take actions\n\n"
        "Respond with ONLY the category word, nothing else."
    )

    result = _call_llm(
        [{"role": "system", "content": sys_msg},
         {"role": "user", "content": prompt[:500]}],
        MODEL_ROUTER.get("classifier", "openai/gpt-4o-mini"),
        max_tokens=20,
    )

    category = (result or "").strip().lower()
    if category not in ("code", "reasoning", "creative", "fast", "vision", "tool"):
        # LLM unavailable or returned unknown category — use regex fallback
        category = _regex_classify(prompt)

    _CLASSIFICATION_CACHE[prompt_stub] = category
    return category


# ─── Router API ─────────────────────────────────────────────────────────

class TaskRouter:
    """Routes tasks to the best model based on LLM classification."""

    @staticmethod
    def route(prompt: str) -> Tuple[str, str]:
        """Get (category, model_id) for a prompt."""
        category = classify_task(prompt)
        model = MODEL_ROUTER.get(category, MODEL_ROUTER["reasoning"])
        return category, model

    @staticmethod
    def classify(prompt: str) -> str:
        return classify_task(prompt)

    @staticmethod
    def get_model(prompt: str) -> str:
        _, model = TaskRouter.route(prompt)
        return model

    @staticmethod
    def call(messages: list, model_id: str = None,
             max_tokens: int = 2000, temperature: float = 0.3) -> Optional[str]:
        """Call an LLM with failover."""
        model = model_id or MODEL_ROUTER["reasoning"]
        return _call_llm(messages, model, max_tokens, temperature)

    @staticmethod
    def status() -> dict:
        return {
            "routes": MODEL_ROUTER,
            "providers": [
                {"name": k, "configured": bool(v[1])}
                for k, v in PROVIDERS.items()
            ],
        }
