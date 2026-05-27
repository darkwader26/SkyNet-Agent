"""Router status tool — inspect the model router and provider health."""

import json
from skynet.registry import registry
from skynet.router import TaskRouter
from skynet.config import MODEL_ROUTER, PROVIDERS


def router_status() -> str:
    """Show the current model routing configuration and provider health."""
    status = TaskRouter.status()
    return json.dumps(status)


# ─── Register ────────────────────────────────────────────────────────────

registry.register("router_status", router_status, {
    "type": "object",
    "properties": {},
}, "Show model routing configuration", "utility")
