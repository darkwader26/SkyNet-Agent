"""Enhanced tool registry — dynamic registration, validation, reload, and removal."""

import os
import json
import ast
import importlib
import importlib.util
import sys
import traceback
from typing import Callable, Dict, Any, Optional, List


class ToolRegistry:
    """Dynamic tool registry with validation, reload, and removal.

    Key capability: the agent can write a new .py file to tools/,
    call reload(), and use the new tool immediately.
    """

    def __init__(self, tools_dir: str = "tools"):
        self.tools_dir = tools_dir
        self._tools: Dict[str, dict] = {}
        self._loaded_modules: Dict[str, Any] = {}
        self._load_builtins()
        # NOTE: reload() is NOT called here — it's deferred to avoid
        # circular imports (tools import registry).
        # Call registry.reload() explicitly after all imports settle.

    def register(self, name: str, fn: Callable, schema: dict,
                 description: str = "", category: str = "general") -> None:
        """Register a tool function with its JSON schema."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "category": category,
            "function": fn,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": schema,
                },
            },
        }

    def unregister(self, name: str) -> bool:
        """Remove a tool by name."""
        return bool(self._tools.pop(name, None))

    def get_schemas(self, exclude: List[str] = None) -> list:
        """Get tool schemas in OpenAI format, optionally excluding some."""
        exclude = exclude or []
        return [
            t["schema"] for n, t in self._tools.items()
            if n not in exclude
        ]

    def get_schema(self, name: str) -> Optional[dict]:
        t = self._tools.get(name)
        return t["schema"] if t else None

    def dispatch(self, name: str, args: dict) -> str:
        """Execute a tool by name. Returns JSON string."""
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: '{name}'"})
        try:
            result = tool["function"](**args)
            return json.dumps({"success": True, "result": result})
        except Exception as e:
            tb = traceback.format_exc()
            return json.dumps({"error": str(e), "traceback": tb})

    def list_tools(self, category: str = None) -> List[str]:
        if category:
            return [n for n, t in self._tools.items() if t["category"] == category]
        return list(self._tools.keys())

    def get_tool_info(self, name: str) -> Optional[dict]:
        t = self._tools.get(name)
        if not t:
            return None
        return {
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
        }

    def reload(self) -> int:
        """Scan tools_dir for new .py files and load them.
        Returns count of newly loaded modules.
        """
        count = 0
        if not os.path.isdir(self.tools_dir):
            os.makedirs(self.tools_dir, exist_ok=True)
            return count

        for fname in sorted(os.listdir(self.tools_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            mod_name = fname[:-3]
            if mod_name in self._loaded_modules:
                continue
            filepath = os.path.join(self.tools_dir, fname)

            # Syntax check before loading
            try:
                with open(filepath) as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                print(f"  ⚠️  Tool '{mod_name}': syntax error — {e}")
                continue

            spec = importlib.util.spec_from_file_location(mod_name, filepath)
            if spec and spec.loader:
                try:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    self._loaded_modules[mod_name] = mod
                    count += 1
                except Exception as e:
                    print(f"  ⚠️  Tool '{mod_name}': load error — {e}")
        return count

    def validate_code(self, code: str) -> Optional[str]:
        """Validate Python code for a new tool. Returns error message or None."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax error: {e}"
        has_function = any(
            isinstance(n, ast.FunctionDef) for n in ast.walk(tree)
        )
        if not has_function:
            return "Code must contain at least one function definition"
        return None

    def _load_builtins(self) -> None:
        """Register built-in tools that always exist."""

        def echo(text: str) -> str:
            return text

        self.register("echo", echo, {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo back"},
            },
            "required": ["text"],
        }, "Echo back the given text", "utility")

        def list_tools(category: str = "") -> list:
            return self.list_tools(category=category or None)

        self.register("list_tools", list_tools, {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category (optional)"},
            },
        }, "List all registered tools", "utility")

        def get_time() -> str:
            from datetime import datetime
            return datetime.now().isoformat()

        self.register("get_time", get_time, {
            "type": "object",
            "properties": {},
        }, "Get the current date and time", "utility")


# Global singleton
registry = ToolRegistry()
