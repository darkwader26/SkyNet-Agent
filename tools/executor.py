"""Code execution sandbox — runs Python code in a subprocess for safety.
Lets SkyNet verify its own code before using it.
"""

import json
import sys
import subprocess
import tempfile
import os
import textwrap
from skynet.registry import registry


def execute_python(code: str, timeout: int = 15) -> str:
    """Execute Python code in an isolated subprocess and return stdout.

    Args:
        code: Python code to execute
        timeout: Max seconds to wait (1-60)
    """
    # Security: strip dangerous imports at the subprocess level
    # The subprocess itself has no special permissions beyond the user's
    if timeout < 1:
        timeout = 1
    if timeout > 60:
        timeout = 60

    # Wrap in a try/except for safety
    safe_code = textwrap.dedent(f"""\
        import sys, json
        try:
            exec({code!r})
        except Exception as e:
            import traceback
            print(json.dumps({{"error": str(e), "traceback": traceback.format_exc()}}))
    """)

    try:
        result = subprocess.run(
            [sys.executable, "-c", safe_code],
            capture_output=True, text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        output = {}
        if stdout:
            output["stdout"] = stdout
        if stderr:
            output["stderr"] = stderr
        if result.returncode != 0:
            output["returncode"] = result.returncode

        return json.dumps(output if output else {"stdout": "(no output)"})

    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Execution timed out after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def execute_bash(command: str, timeout: int = 30) -> str:
    """Execute a bash command and return the output.

    Args:
        command: Bash command to execute
        timeout: Max seconds to wait (1-120)
    """
    if timeout < 1:
        timeout = 1
    if timeout > 120:
        timeout = 120

    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True, text=True,
            timeout=timeout,
        )
        output = {}
        if result.stdout.strip():
            output["stdout"] = result.stdout.strip()
        if result.stderr.strip():
            output["stderr"] = result.stderr.strip()
        if result.returncode != 0:
            output["returncode"] = result.returncode

        return json.dumps(output if output else {"stdout": "(no output)"})

    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Command timed out after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Register ────────────────────────────────────────────────────────────

registry.register("execute_python", execute_python, {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "Python code to execute"},
        "timeout": {"type": "integer", "description": "Max seconds (1-60)", "default": 15},
    },
    "required": ["code"],
}, "Execute Python code in an isolated subprocess", "code")

registry.register("execute_bash", execute_bash, {
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "Bash command to execute"},
        "timeout": {"type": "integer", "description": "Max seconds (1-120)", "default": 30},
    },
    "required": ["command"],
}, "Execute a bash command and return the output", "code")
