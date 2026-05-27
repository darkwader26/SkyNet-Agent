"""File system tools — read, write, search, and manage files."""

import json
import os
import fnmatch
from skynet.registry import registry


def read_file(path: str, offset: int = 1, limit: int = 200) -> str:
    """Read a file and return its contents with line numbers.

    Args:
        path: Path to the file (absolute or relative)
        offset: Starting line number (1-based)
        limit: Maximum lines to read (max 500)
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return json.dumps({"error": f"File not found: {path}"})
    if not os.path.isfile(path):
        return json.dumps({"error": f"Not a file: {path}"})

    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return json.dumps({"error": str(e)})

    total = len(lines)
    if offset < 1:
        offset = 1
    if limit > 500:
        limit = 500

    selected = lines[offset - 1 : offset - 1 + limit]
    content = "".join(
        f"{i + offset:4d}|{line}"
        for i, line in enumerate(selected)
    )

    return json.dumps({
        "path": path,
        "total_lines": total,
        "offset": offset,
        "limit": limit,
        "content": content,
    })


def write_file(path: str, content: str) -> str:
    """Write content to a file (overwrites existing content).

    Args:
        path: Path to the file
        content: Content to write
    """
    path = os.path.expanduser(path)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        size = os.path.getsize(path)
        return json.dumps({
            "path": path,
            "bytes_written": size,
            "status": "written",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_files(pattern: str, path: str = ".", file_glob: str = "",
                 max_results: int = 30) -> str:
    """Search for text in files using grep-like pattern matching.

    Args:
        pattern: Search pattern (regex supported)
        path: Directory to search in
        file_glob: Optional file filter (e.g. '*.py')
        max_results: Maximum matches to return
    """
    path = os.path.expanduser(path)
    import subprocess

    cmd = ["grep", "-rn", "--color=never"]
    if file_glob:
        cmd.extend(["--include", file_glob])
    cmd.extend(["-m", str(max_results), pattern, path])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
        )
        matches = result.stdout.strip()
        if not matches:
            return json.dumps({"matches": [], "count": 0})
        lines = matches.split("\n")[:max_results]
        return json.dumps({
            "matches": lines,
            "count": len(lines),
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Search timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def list_files(path: str = ".", pattern: str = "*") -> str:
    """List files in a directory matching a glob pattern.

    Args:
        path: Directory to list
        pattern: Glob pattern (e.g. '*.py', '**/*.md')
    """
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        return json.dumps({"error": f"Directory not found: {path}"})

    try:
        # Use glob for pattern matching
        import glob as glob_mod
        full_pattern = os.path.join(path, pattern) if pattern else os.path.join(path, "*")
        files = sorted(glob_mod.glob(full_pattern, recursive=True))
        # Get file info
        entries = []
        for f in files:
            try:
                stat = os.stat(f)
                entries.append({
                    "name": f,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "is_dir": os.path.isdir(f),
                })
            except OSError:
                pass

        return json.dumps({
            "path": path,
            "pattern": pattern,
            "files": entries,
            "count": len(entries),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Register ────────────────────────────────────────────────────────────

registry.register("read_file", read_file, {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to the file"},
        "offset": {"type": "integer", "description": "Starting line (1-based)", "default": 1},
        "limit": {"type": "integer", "description": "Max lines to read", "default": 200},
    },
    "required": ["path"],
}, "Read a file with line numbers", "filesystem")

registry.register("write_file", write_file, {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to the file"},
        "content": {"type": "string", "description": "Content to write"},
    },
    "required": ["path", "content"],
}, "Write content to a file (overwrites)", "filesystem")

registry.register("search_files", search_files, {
    "type": "object",
    "properties": {
        "pattern": {"type": "string", "description": "Search pattern"},
        "path": {"type": "string", "description": "Directory to search"},
        "file_glob": {"type": "string", "description": "File filter (e.g. '*.py')"},
        "max_results": {"type": "integer", "description": "Max matches", "default": 30},
    },
    "required": ["pattern"],
}, "Search for text in files using grep", "filesystem")

registry.register("list_files", list_files, {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Directory to list"},
        "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
    },
}, "List files in a directory", "filesystem")
