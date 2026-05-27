"""Memory interaction tools — let the agent read and write its own memory."""

import json
from datetime import datetime
from skynet.registry import registry
from skynet.memory import Memory
from skynet.config import load_config


def _get_memory() -> Memory:
    return Memory(load_config().memory_db_path)


def memory_save(key: str, value: str, category: str = "general",
                importance: int = 1) -> str:
    """Save a fact to persistent memory.

    Args:
        key: Unique identifier for this fact
        value: The fact content
        category: Category (e.g. 'user_preference', 'project_info', 'environment')
        importance: Importance 1-5 (5 = most important)
    """
    mem = _get_memory()
    mem.save_fact(key, value, category, importance)
    mem.close()
    return json.dumps({"saved": key, "category": category})


def memory_get(category: str = "") -> str:
    """Retrieve facts from persistent memory.

    Args:
        category: Optional filter (e.g. 'user_preference')
    """
    mem = _get_memory()
    facts = mem.get_facts(category=category or None)
    mem.close()
    return json.dumps({"facts": facts, "count": len(facts)})


def memory_delete(key: str) -> str:
    """Delete a fact from memory.

    Args:
        key: The fact key to delete
    """
    mem = _get_memory()
    mem.delete_fact(key)
    mem.close()
    return json.dumps({"deleted": key})


def memory_search(query: str, limit: int = 5) -> str:
    """Search past conversations.

    Args:
        query: Search terms
        limit: Max results
    """
    mem = _get_memory()
    results = mem.search_sessions(query, limit)
    mem.close()
    return json.dumps({"results": results, "count": len(results)})


# ─── Register ────────────────────────────────────────────────────────────

registry.register("memory_save", memory_save, {
    "type": "object",
    "properties": {
        "key": {"type": "string", "description": "Unique fact key"},
        "value": {"type": "string", "description": "Fact content"},
        "category": {"type": "string", "description": "Category"},
        "importance": {"type": "integer", "description": "Importance 1-5", "default": 1},
    },
    "required": ["key", "value"],
}, "Save a fact to persistent memory", "memory")

registry.register("memory_get", memory_get, {
    "type": "object",
    "properties": {
        "category": {"type": "string", "description": "Optional category filter"},
    },
}, "Retrieve facts from memory", "memory")

registry.register("memory_delete", memory_delete, {
    "type": "object",
    "properties": {
        "key": {"type": "string", "description": "Fact key to delete"},
    },
    "required": ["key"],
}, "Delete a fact from memory", "memory")

registry.register("memory_search", memory_search, {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search terms"},
        "limit": {"type": "integer", "description": "Max results", "default": 5},
    },
    "required": ["query"],
}, "Search past conversations", "memory")
