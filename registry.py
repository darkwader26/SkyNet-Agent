"""Tool registry — dynamic tool registration, discovery, and reload.

The agent can register new tools at runtime, enabling infinite expansion.
Every solved problem leaves behind a reusable tool.
"""

import os
import json
import importlib
import importlib.util
from typing import Callable, Dict, Any, Optional


class ToolRegistry:
    """Central tool registry with dynamic reload support."""
    
    def __init__(self, tools_dir: str = "tools"):
        self.tools_dir = tools_dir
        self._tools: Dict[str, dict] = {}
        self._register_builtins()
        self.reload()
    
    def register(self, name: str, fn: Callable, schema: dict,
                 description: str = "") -> None:
        """Register a tool function with its JSON schema."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "function": fn,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": schema,
                }
            }
        }
    
    def get_schemas(self) -> list:
        """Get all tool schemas in OpenAI format for LLM tool calling."""
        return [t["schema"] for t in self._tools.values()]
    
    def dispatch(self, name: str, args: dict) -> str:
        """Call a tool by name with the given arguments."""
        if name not in self._tools:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = self._tools[name]["function"](**args)
            return json.dumps({"success": True, "result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_tools(self) -> list:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def reload(self) -> int:
        """Scan tools_dir for new .py files and load them.
        
        This is the key capability — the agent can create a new tool file,
        call reload(), and immediately use the new tool.
        """
        count = 0
        if not os.path.isdir(self.tools_dir):
            return count
        
        for fname in sorted(os.listdir(self.tools_dir)):
            if fname.endswith(".py") and not fname.startswith("_"):
                mod_name = fname[:-3]
                filepath = os.path.join(self.tools_dir, fname)
                spec = importlib.util.spec_from_file_location(mod_name, filepath)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    count += 1
        return count
    
    def _register_builtins(self) -> None:
        """Register tools that always exist."""
        
        def echo(text: str) -> str:
            return text
        
        self.register("echo", echo,
            {"type": "object", "properties": {
                "text": {"type": "string", "description": "Text to echo"}
            }, "required": ["text"]},
            "Echo back the given text")


# Global singleton
registry = ToolRegistry()
