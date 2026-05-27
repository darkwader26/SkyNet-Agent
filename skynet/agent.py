"""The SkyNet Agent — core conversation loop.

Pattern: system prompt + tools → LLM → parse tool calls → dispatch → append → repeat
Supports streaming, multi-provider, session persistence, and self-improvement.
"""

import json
import os
import sys
import re
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from openai import OpenAI

from .config import load_config, AgentConfig, PROVIDERS, resolve_model
from .registry import registry
from .memory import Memory
from .router import TaskRouter
from .improv import SelfImprovement
from .daemon import BackgroundDaemon


class SkyNetAgent:
    """The agent itself. Manages the conversation loop, state, and learning."""

    def __init__(self, config: AgentConfig = None):
        self.config = config or load_config()
        self.session_id = self.config.session_id or self._make_session_id()

        # Reload tool modules (deferred to avoid circular imports)
        loaded = registry.reload()
        if loaded:
            print(f"  🔧 Loaded {loaded} tool module(s)")

        # Core systems
        self.memory = Memory(self.config.memory_db_path)
        self.router = TaskRouter()
        self.improver = SelfImprovement(
            system_prompt_path=self.config.system_prompt_path,
            memory=self.memory,
            improvement_llm=self.config.improvement_llm,
        )

        # Daemon
        self.daemon = BackgroundDaemon(
            interval_sec=self.config.daemon_interval_sec,
        )

        # Wire up daemon alert handler
        self.daemon.set_alert_handler(self._on_daemon_alert)

        # Session state
        self.system_prompt = self._load_system_prompt()
        self.history: List[dict] = []
        self._session_loaded = False
        self._tool_count = 0
        self._turn_count = 0
        self._pending_approval: Optional[dict] = None
        self._last_error: Optional[str] = None

        # Apply pending lessons at startup
        if self.config.auto_improve:
            applied = self.improver.apply_pending_lessons()
            if applied:
                self.system_prompt = self._load_system_prompt()

    # ── Session Management ──────────────────────────────────────────────

    def _make_session_id(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:6]

    def resume_session(self, session_id: str) -> bool:
        """Load a previous session's history."""
        sess = self.memory.get_session(session_id)
        if not sess:
            return False
        self.session_id = session_id
        msgs = self.memory.get_history(session_id)
        for msg in msgs:
            if msg["role"] in ("user", "assistant"):
                self.history.append({"role": msg["role"], "content": msg["content"]})
        self._session_loaded = True
        print(f"  📝 Resumed session: {sess.get('title', session_id)} "
              f"({len(msgs)} messages)")
        return True

    def _load_system_prompt(self) -> str:
        path = self.config.system_prompt_path
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
                # Inject session context
                context = (
                    f"\n\n# Session Context\n\n"
                    f"- Session ID: `{self.session_id}`\n"
                    f"- Tools available: {len(registry.list_tools())}\n"
                    f"- Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                # Inject memory facts if any
                facts = self.memory.get_facts()
                if facts:
                    context += "\n# Remembered Facts\n\n"
                    for f in facts:
                        context += f"- [{f['category']}] {f['key']}: {f['value']}\n"
                return content + context
        return "You are SkyNet, an autonomous AI agent with tool access, self-improvement, and memory."

    def _save_and_refresh_prompt(self) -> None:
        """Re-read system prompt (lessons may have been applied)."""
        self.system_prompt = self._load_system_prompt()

    # ── Daemon Integration ──────────────────────────────────────────────

    def _on_daemon_alert(self, task_name: str, result: dict) -> None:
        """Called when a daemon task fires an alert."""
        msg = result.get("message", f"Daemon task '{task_name}' triggered")
        print(f"\n  🔔 [DAEMON] {msg}")

    def start_daemon(self) -> None:
        """Start the background daemon in a thread."""
        import threading
        t = threading.Thread(target=self._run_daemon, daemon=True)
        t.start()
        print(f"  ⏱️  Daemon thread started")

    def _run_daemon(self) -> None:
        """Run daemon in async event loop."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.daemon.run_loop())

    # ── LLM Interaction ────────────────────────────────────────────────

    def _get_client(self, model_id: str) -> tuple:
        """Get (OpenAI client, actual_model_name) with provider resolution."""
        if model_id.count("/") == 1 and not model_id.startswith(("gpt", "o1", "o3")):
            provider, model_name = model_id.split("/", 1)
            info = PROVIDERS.get(provider)
            if info and info[1]:  # has API key
                return OpenAI(base_url=info[0], api_key=info[1], timeout=60), model_name
        # Fallback to direct OpenAI
        base, key, _ = PROVIDERS.get("openai", ("", "", ""))
        if key:
            return OpenAI(base_url=base, api_key=key, timeout=60), model_id
        return OpenAI(timeout=60), model_id

    def _llm_call(self, messages: list, model_id: str,
                  tools: list = None, stream: bool = True,
                  max_tokens: int = 4096) -> dict:
        """Make an LLM call with optional tool calling and streaming."""
        client, model = self._get_client(model_id)
        kwargs = dict(model=model, messages=messages, max_tokens=max_tokens)

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        if stream and not tools:
            kwargs["stream"] = True
            return self._handle_stream(client, **kwargs)
        else:
            kwargs["stream"] = False
            resp = client.chat.completions.create(**kwargs)
            return {"type": "complete", "message": resp.choices[0].message}

    def _handle_stream(self, client, **kwargs) -> dict:
        """Handle streaming response."""
        stream = kwargs.pop("stream", True)
        kwargs["stream"] = True
        response = client.chat.completions.create(**kwargs)
        collected = []
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                collected.append(delta.content)
                print(delta.content, end="", flush=True)
        print()
        return {"type": "stream", "content": "".join(collected)}

    # ── Tool Execution ─────────────────────────────────────────────────

    def _execute_tools(self, tool_calls: list) -> List[dict]:
        """Execute tool calls and return tool result messages."""
        results = []
        for tc in tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                fn_args = {}

            self._tool_count += 1

            # ── Approval gate ──
            approval_result = self._check_approval(fn_name, fn_args)
            if approval_result:
                result = json.dumps(approval_result)
            else:
                result = registry.dispatch(fn_name, fn_args)
                # Check for errors, trigger learning
                parsed = json.loads(result)
                if "error" in parsed:
                    self._last_error = parsed["error"]
                    if self.config.auto_improve:
                        self.improver.learn_from_failure(
                            situation=f"tool_call: {fn_name}",
                            action=json.dumps(fn_args),
                            outcome=parsed["error"],
                            session_id=self.session_id,
                        )
                else:
                    self._last_error = None

            status = "✅" if '"success": true' in result else "⚠️"
            print(f"  {status} {fn_name}(...)")

            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        return results

    def _check_approval(self, name: str, args: dict) -> Optional[dict]:
        """Check if a tool needs manual approval."""
        mode = self.config.approval_mode
        if mode == "off":
            return None
        if name in self.config.approval_exempt:
            return None
        if mode == "smart":
            # In smart mode, only flag truly dangerous actions
            dangerous_keywords = ["rm ", "del ", "drop ", "format ", "shutdown"]
            args_str = json.dumps(args).lower()
            if not any(k in args_str for k in dangerous_keywords):
                return None
        # Would need user input — for CLI mode, return a blocked message
        return {
            "error": f"Tool '{name}' requires manual approval. "
                     f"Run with --yolo to bypass or approval_mode=off in config."
        }

    # ── Tool Generation ────────────────────────────────────────────────

    def _generate_tool(self, prompt: str) -> None:
        """Generate a new tool from a natural language description."""
        print(f"  🛠️  Generating tool: '{prompt}'")
        model = self.config.toolgen_model

        gen_prompt = (
            "You are a tool generator. Write a Python function with a JSON schema.\n\n"
            f"User request: {prompt}\n\n"
            "Requirements:\n"
            "- Pure function with no side effects (unless documented)\n"
            "- Type hints and docstring\n"
            "- Return a JSON-serializable value\n"
            "- Respond with ONLY the Python code in a ```python block\n\n"
            "Format:\n"
            "```python\n"
            "def tool_name(param1: type, param2: type = default) -> return_type:\n"
            '    """Description."""\n'
            "    # implementation\n"
            "    return result\n"
            "```"
        )

        client, actual_model = self._get_client(model)
        try:
            resp = client.chat.completions.create(
                model=actual_model,
                messages=[{"role": "user", "content": gen_prompt}],
                max_tokens=2000,
                temperature=0.2,
            )
        except Exception as e:
            print(f"  ❌ Generation failed: {e}")
            return

        code_block = resp.choices[0].message.content or ""

        # Extract code from markdown block
        match = re.search(r"```python\s*\n(.*?)```", code_block, re.DOTALL)
        code = match.group(1).strip() if match else code_block.strip()

        # Validate syntax
        error = registry.validate_code(code)
        if error:
            print(f"  ❌ Validation error: {error}")
            return

        # Extract function name
        match = re.search(r"def (\w+)\(", code)
        if not match:
            print("  ❌ Could not find function definition")
            return

        fn_name = match.group(1)
        os.makedirs(self.config.tools_dir, exist_ok=True)
        file_path = os.path.join(self.config.tools_dir, f"{fn_name}.py")

        # Build full module with auto-registration
        full_module = (
            f'"""Auto-generated tool: {fn_name}"""\n\n'
            f'from skynet.registry import registry\n\n\n'
            f'{code}\n\n'
            f'# Auto-register\n'
            f'registry.register(\n'
            f'    "{fn_name}", {fn_name},\n'
            f'    {{"type": "object", "properties": {{}}, "required": []}},\n'
            f'    {fn_name}.__doc__ or "",\n'
            f'    category="generated",\n'
            f')\n'
        )

        with open(file_path, "w") as f:
            f.write(full_module)

        count = registry.reload()
        print(f"  ✅ Tool '{fn_name}' registered! ({len(registry.list_tools())} tools total)")
        print(f"  📁 Saved: {file_path}")

    # ── Main Loop ──────────────────────────────────────────────────────

    def run(self):
        """Run the main conversation loop."""
        print(f"\n{'='*55}")
        print(f"  🤖 SkyNet Agent")
        print(f"  Session: {self.session_id}")
        print(f"  Model:   {self.config.default_model}")
        print(f"  Tools:   {len(registry.list_tools())} registered")
        print(f"  Memory:  {len(self.memory.get_facts())} facts stored")
        if self.config.auto_improve:
            impr = self.improver.status()
            print(f"  Lessons: {impr['pending_lessons']} pending, "
                  f"{impr['lessons_applied_this_session']} applied")
        print(f"{'='*55}")
        print(f"  Commands: /quit | /new | /save <name> | /resume <id>")
        print(f"            /tools | /facts | /learn | toolgen <desc>")
        print()

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  👋 Goodbye!")
                self._cleanup()
                break

            if not user_input:
                continue

            # ── Slash commands ──
            if user_input.startswith("/"):
                self._handle_slash(user_input)
                continue

            # ── Tool generation ──
            if user_input.lower().startswith("toolgen "):
                self._generate_tool(user_input[8:])
                self._save_and_refresh_prompt()
                continue

            # ── Normal conversation ──
            self._handle_message(user_input)

    def _handle_message(self, user_input: str) -> None:
        """Process a user message through the LLM loop."""
        self.history.append({"role": "user", "content": user_input})

        # Save to memory
        self.memory.save_message(self.session_id, "user", user_input)

        self._turn_count = 0
        messages = [{"role": "system", "content": self.system_prompt}] + self.history[-20:]

        for turn in range(self.config.max_turns):
            self._turn_count += 1

            # Classify and route
            category, model_id = self.router.route(user_input)

            tools = registry.get_schemas()

            try:
                result = self._llm_call(
                    messages, model_id,
                    tools=tools if tools else None,
                    stream=self.config.stream,
                )
            except Exception as e:
                print(f"  ❌ LLM error: {e}")
                # Try without tools as fallback
                try:
                    result = self._llm_call(
                        messages, model_id,
                        tools=None, stream=False,
                    )
                except Exception as e2:
                    print(f"  ❌ Fallback also failed: {e2}")
                    break

            if result["type"] == "stream":
                # Streaming response — already printed
                content = result.get("content", "")
                if content:
                    self.history.append({"role": "assistant", "content": content})
                    self.memory.save_message(self.session_id, "assistant", content)
                break

            msg = result.get("message")
            if not msg:
                break

            if msg.tool_calls:
                tool_results = self._execute_tools(msg.tool_calls)

                messages.append({"role": "assistant", "content": None, "tool_calls": msg.tool_calls})
                messages.extend(tool_results)
                continue
            else:
                content = msg.content or ""
                if content:
                    print(f"\n🤖 {content}\n")
                    self.history.append({"role": "assistant", "content": content})
                    self.memory.save_message(self.session_id, "assistant", content)
                break

        # After message: auto-improve
        if self.config.auto_improve and self._turn_count > 1:
            applied = self.improver.apply_pending_lessons()
            if applied:
                self._save_and_refresh_prompt()
                print(f"  🧠 Learned {applied} new rule(s) from experience")

    # ── Slash Commands ──────────────────────────────────────────────────

    def _handle_slash(self, cmd: str) -> None:
        parts = cmd[1:].strip().split(maxsplit=1)
        verb = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if verb in ("quit", "exit"):
            print("  👋 Goodbye!")
            self._cleanup()
            sys.exit(0)

        elif verb in ("new", "reset"):
            self.history = []
            self.session_id = self._make_session_id()
            self._save_and_refresh_prompt()
            print(f"  🆕 New session: {self.session_id}")

        elif verb == "save" and arg:
            self.memory.update_session_title(self.session_id, arg)
            print(f"  💾 Session saved as: {arg}")

        elif verb == "resume" and arg:
            if self.resume_session(arg):
                self._save_and_refresh_prompt()
                title = self.memory.get_session(arg)
                print(f"  📝 Resumed! {title.get('title', '') if title else ''}")
            else:
                sessions = self.memory.list_sessions(5)
                print(f"  ❌ Session '{arg}' not found. Recent sessions:")
                for s in sessions:
                    print(f"     {s['id']}: {s.get('title', 'Untitled')} — {s.get('created_at', '')}")

        elif verb == "tools":
            cats = {}
            for t in registry.list_tools():
                info = registry.get_tool_info(t)
                cat = info["category"] if info else "unknown"
                cats.setdefault(cat, []).append(t)
            print(f"  🔧 Tools ({len(registry.list_tools())}):")
            for cat, tools in cats.items():
                print(f"     [{cat}] {', '.join(tools)}")

        elif verb == "facts":
            facts = self.memory.get_facts()
            if facts:
                print(f"  📌 Facts ({len(facts)}):")
                for f in facts:
                    print(f"     [{f['category']}] {f['key']}: {f['value']}")
            else:
                print("  📌 No facts stored yet")

        elif verb == "learn":
            status = self.improver.status()
            applied = self.improver.apply_pending_lessons()
            if applied:
                self._save_and_refresh_prompt()
                print(f"  🧠 Applied {applied} learned rules")
            else:
                print(f"  🧠 {status['pending_lessons']} pending, "
                      f"{status['lessons_applied_this_session']} applied this session")

        elif verb == "sessions":
            sessions = self.memory.list_sessions(10)
            if sessions:
                print(f"  📚 Recent sessions:")
                for s in sessions:
                    print(f"     {s['id']}: {s.get('title', 'Untitled')} "
                          f"({s.get('created_at', '')})")
            else:
                print("  📚 No saved sessions")

        elif verb == "search" and arg:
            results = self.memory.search_sessions(arg, limit=5)
            if results:
                print(f"  🔍 Search results for '{arg}':")
                for r in results:
                    print(f"     {r['id']}: {r.get('title', '')}")
                    print(f"       {r.get('snippet', '')[:120]}...")
            else:
                print(f"  🔍 No results for '{arg}'")

        elif verb == "route" and arg:
            cat, model = self.router.route(arg)
            print(f"  🎯 Classification: {cat}")
            print(f"  🎯 Model: {model}")

        elif verb == "consolidate":
            count = self.improver.consolidate_rules()
            print(f"  🧹 Consolidated to {count} rules in system prompt")

        elif verb in ("help", "?"):
            print("  /quit         Exit")
            print("  /new          New session")
            print("  /save <name>  Name this session")
            print("  /resume <id>  Resume previous session")
            print("  /sessions     List recent sessions")
            print("  /search <q>   Search past conversations")
            print("  /tools        List registered tools")
            print("  /facts        Show remembered facts")
            print("  /learn        Apply pending lessons")
            print("  /route <q>    Classify a task")
            print("  /consolidate  Consolidate learned rules")
            print("  toolgen ...   Generate a new tool")

    def _cleanup(self) -> None:
        """Cleanup on exit."""
        self.memory.close()
