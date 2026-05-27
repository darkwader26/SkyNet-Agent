"""Core conversation loop — the heart of the agent.

Pattern: system prompt + tools → LLM → parse tool calls → dispatch → append results → loop
Special mode: 'toolgen <prompt>' generates a new tool at runtime.
"""

import json
import os
import sys
import re
from openai import OpenAI

from config import load_config, MODEL_ROUTER, PROVIDERS
from registry import registry


def get_client(model_id: str) -> tuple:
    """Get the right client and model string for a given model ID."""
    if "/" in model_id:
        provider_prefix, actual_model = model_id.split("/", 1)
        if provider_prefix in PROVIDERS:
            base_url, api_key, _ = PROVIDERS[provider_prefix]
            if api_key:
                return OpenAI(base_url=base_url, api_key=api_key), actual_model
    return OpenAI(), model_id


def load_system_prompt(path: str) -> str:
    """Load the system prompt, with fallback default."""
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return "You are a helpful AI assistant with tool access."


def run_conversation(system_prompt_path: str = "system_prompt.md",
                     model: str = None) -> None:
    """Run the main conversation loop."""
    config = load_config()
    model = model or MODEL_ROUTER["reasoning"]
    system_prompt = load_system_prompt(system_prompt_path)
    
    client, actual_model = get_client(model)
    history = []
    
    print(f"\n{'='*50}")
    print(f"  🤖 SkyNet Agent ready")
    print(f"  Model: {model}")
    print(f"  Tools: {len(registry.list_tools())} registered")
    print(f"{'='*50}")
    print(f"  Commands: /quit to exit | 'toolgen <prompt>' to create a new tool")
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            break
        
        # ── Tool generation mode ──
        if user_input.lower().startswith("toolgen "):
            prompt = user_input[8:]
            _handle_tool_gen(prompt, config)
            continue
        
        # ── Normal conversation ──
        history.append({"role": "user", "content": user_input})
        messages = [{"role": "system", "content": system_prompt}] + history
        
        for turn in range(config.max_turns):
            tools = registry.get_schemas()
            
            kwargs = dict(model=actual_model, messages=messages)
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}
                    
                    result = registry.dispatch(fn_name, fn_args)
                    status = "success" if '"success": true' in result else "error"
                    print(f"  🔧 {fn_name}(...) → {status}")
                    
                    messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            else:
                response_text = msg.content or ""
                print(f"\n🤖 {response_text}\n")
                history.append({"role": "assistant", "content": response_text})
                break
        else:
            print("  ⚠️  Max turns reached. Resuming...")


def _handle_tool_gen(prompt: str, config) -> None:
    """Generate a new tool from a natural language description."""
    print(f"  🛠️  Generating tool from: '{prompt}'")
    
    client, model = get_client(MODEL_ROUTER["code"])
    
    gen_prompt = f"""You are a tool generator. Write a Python function with a JSON schema.

User request: {prompt}

Requirements:
- Pure function, no side effects unless documented
- Include type hints and docstring
- Return a JSON-serializable value
- Respond with ONLY the Python code

Format:
```python
def tool_name(param1: type, param2: type = default) -> return_type:
    \"\"\"Description.\"\"\"
    # implementation
    return result
```
"""
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": gen_prompt}],
    )
    
    code = response.choices[0].message.content or ""
    
    # Extract function name
    match = re.search(r"def (\w+)\(", code)
    if not match:
        print("  ❌ Could not parse function from generated code")
        return
    
    fn_name = match.group(1)
    os.makedirs(config.tools_dir, exist_ok=True)
    file_path = os.path.join(config.tools_dir, f"{fn_name}.py")
    
    # Wrap with auto-registration
    full_code = f'''"""Auto-generated tool: {fn_name}"""

from registry import registry


{code}

# Auto-register
schema = {{
    "type": "object",
    "properties": {{}},
    "required": []
}}
registry.register("{fn_name}", {fn_name}, schema, {fn_name}.__doc__ or "")
'''
    
    with open(file_path, "w") as f:
        f.write(full_code)
    
    count = registry.reload()
    print(f"  ✅ Tool '{fn_name}' created and registered! ({len(registry.list_tools())} tools total)")
    print(f"  📁 Saved to {file_path}")


if __name__ == "__main__":
    run_conversation()
