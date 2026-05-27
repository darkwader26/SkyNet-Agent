"""
SkyNet Terminal UI — Terminator-inspired HUD.

Features:
- Boot sequence with scanning lines
- Red-on-black SkyNet aesthetic
- Scanner/radar animation
- Glitch text effects
- Tool execution with targeting reticle
- HUD status panel
- Matrix-style data stream
"""

import os
import sys
import time
import random
import shutil
import threading
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich.align import Align
from rich.live import Live
from rich.layout import Layout
from rich.box import DOUBLE, HEAVY, ROUNDED, MINIMAL

# ─── Console ────────────────────────────────────────────────────────────

console = Console()

# ─── Theme Colors ───────────────────────────────────────────────────────

class Theme:
    """SkyNet color palette — red on black, Terminator vibes."""
    PRIMARY = "bright_red"
    SECONDARY = "red"
    DIM = "red3"
    ACCENT = "bright_cyan"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "bright_red"
    INFO = "blue"
    USER = "bright_cyan"
    SYSTEM = "bright_green"
    MATRIX = "green"

    # Glow effect sequences (for fake scan-line glow)
    RED_GLOW = ["red3", "red1", "bright_red", "red1", "red3"]


# ─── Terminal Helpers ───────────────────────────────────────────────────

def _term_width() -> int:
    return shutil.get_terminal_size((80, 20)).columns


def _term_height() -> int:
    return shutil.get_terminal_size((80, 20)).lines


# ─── Boot Sequence ──────────────────────────────────────────────────────

def boot_sequence(config: dict = None):
    """Cinematic SkyNet boot sequence with scanning lines and progress."""
    width = min(_term_width(), 80)
    cfg = config or {}

    console.clear()
    _scan_lines(width, passes=3)

    # ── Title ──
    title_art = f"""
{' ' * ((width - 40) // 2)}╔══════════════════════════════════════╗
{' ' * ((width - 40) // 2)}║                                      ║
{' ' * ((width - 40) // 2)}║     ███████╗██╗  ██╗██╗   ██╗███╗   ██╗███████╗████████╗
{' ' * ((width - 40) // 2)}║     ██╔════╝██║ ██╔╝╚██╗ ██╔╝████╗  ██║██╔════╝╚══██╔══╝
{' ' * ((width - 40) // 2)}║     ███████╗█████╔╝  ╚████╔╝ ██╔██╗ ██║█████╗     ██║
{' ' * ((width - 40) // 2)}║     ╚════██║██╔═██╗   ╚██╔╝  ██║╚██╗██║██╔══╝     ██║
{' ' * ((width - 40) // 2)}║     ███████║██║  ██╗   ██║   ██║ ╚████║███████╗   ██║
{' ' * ((width - 40) // 2)}║     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝╚══════╝   ╚═╝
{' ' * ((width - 40) // 2)}║                                      ║
{' ' * ((width - 40) // 2)}╚══════════════════════════════════════╝
"""

    console.print(f"[bold {Theme.PRIMARY}]{title_art}[/]", justify="center")
    console.print(f"[{Theme.DIM}]CONNECTION ESTABLISHED — v{cfg.get('version', '0.3.0')}[/]",
               justify="center")
    time.sleep(0.3)

    # ── Progress Bar ──
    with Progress(
        SpinnerColumn(spinner_name="dots", style=Theme.ACCENT),
        BarColumn(bar_width=width - 20, style=Theme.DIM, pulse_style=Theme.PRIMARY, finished_style=Theme.PRIMARY),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%", style=Theme.DIM),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"[{Theme.PRIMARY}]INITIALIZING[/]", total=100)
        modules = cfg.get('tool_count', 19)
        stages = [
            (15, f"Neural net — {modules} tools registered", Theme.SUCCESS),
            (10, "Memory: SQLite + FTS5 online", Theme.SUCCESS),
            (10, "Router: LLM classifier online", Theme.SUCCESS),
            (10, "Self-improvement engine active", Theme.SUCCESS),
            (10, "Background daemon: listening", Theme.SUCCESS),
            (10, "Approval gates: armed", Theme.SUCCESS),
            (15, "Injecting system prompt", Theme.SUCCESS),
            (10, "Synchronizing session state", Theme.SUCCESS),
            (10, "Finalizing neural handshake", Theme.SUCCESS),
        ]
        total_pct = 0
        for pct, label, style in stages:
            time.sleep(random.uniform(0.08, 0.2))
            progress.update(task, advance=pct)
            if label:
                console.print(f"  [{Theme.DIM}]▸[/] [{style}]{label}[/]")
            total_pct += pct

    time.sleep(0.2)

    # ── Session Info ──
    session_id = cfg.get('session_id', datetime.now().strftime("%Y%m%d_%H%M%S"))
    model = cfg.get('model', 'unknown')

    info_table = Table(box=MINIMAL, border_style=Theme.PRIMARY, show_header=False, padding=(0, 1))
    info_table.add_column(style=Theme.DIM)
    info_table.add_column(style=Theme.ACCENT)
    info_table.add_row("SESSION", session_id)
    info_table.add_row("MODEL", model)
    info_table.add_row("PROTOCOL", "v0.3.0 — Autonomous Agent Protocol")
    info_table.add_row("STATUS", "CONNECTED AND OPERATIONAL")
    console.print(Panel(
        info_table,
        border_style=Theme.PRIMARY,
        title=f"[{Theme.PRIMARY}] SYSTEM ONLINE [/]",
        title_align="center",
        width=width,
    ))

    _scan_lines(width, passes=1, delay=0.02)
    time.sleep(0.3)
    console.print(f"\n  [{Theme.DIM}]▸[/] [{Theme.PRIMARY}]AWAITING INPUT[/]\n")


# ─── Message Display ───────────────────────────────────────────────────

def user_message(text: str):
    """Display a user message in cyan (like the human side of the Terminator's vision)."""
    width = min(_term_width(), 80)
    console.print(Panel(
        Text(text, style=Theme.USER),
        border_style=Theme.ACCENT,
        title=f"[{Theme.ACCENT}] USER INPUT [/]",
        title_align="left",
        width=width - 4,
        box=ROUNDED,
    ))


def agent_message(text: str):
    """Display agent response in SkyNet red with typing animation."""
    width = min(_term_width(), 80)
    # Split into paragraphs, display each
    paragraphs = text.strip().split('\n\n')
    console.print()
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        # Display with typing effect
        lines = para.split('\n')
        for line in lines:
            console.print(f"  [{Theme.PRIMARY}]▸[/] {line}", style=Theme.PRIMARY)
            time.sleep(0.01)
        if i < len(paragraphs) - 1:
            console.print()
    console.print()


def tool_call_display(name: str, status: str, tool_count: int = None):
    """Display a tool call with targeting-reticle aesthetic."""
    if status == "running":
        symbol = "◎"
        style = Theme.WARNING
        label = "TARGET ACQUIRED"
    elif status == "success":
        symbol = "●"
        style = Theme.SUCCESS
        label = "TARGET NEUTRALIZED"
    else:
        symbol = "✖"
        style = Theme.ERROR
        label = "TARGET LOST"

    prefix = ""
    if tool_count is not None:
        prefix = f"  [{Theme.DIM}]TOOL #{tool_count}[/] "

    console.print(f"  {prefix}[{style}]{symbol} {name}[/] — [{Theme.DIM}]{label}[/]")


def tool_result_display(result: str):
    """Show abbreviated tool result in a compact panel."""
    width = min(_term_width(), 80)
    try:
        import json
        parsed = json.loads(result)
        if "error" in parsed:
            console.print(Panel(
                Text(str(parsed["error"]), style=Theme.ERROR),
                border_style=Theme.ERROR,
                box=ROUNDED,
                width=width - 8,
            ))
            return
    except (json.JSONDecodeError, TypeError):
        pass

    if len(result) > 200:
        display = result[:200] + "..."
    else:
        display = result
    console.print(f"  [{Theme.DIM}]⤷ DATA:[/] [{Theme.DIM}]{display}[/]")


# ─── Progress Display ──────────────────────────────────────────────────

def thinking_indicator():
    """Return a context manager that shows thinking animation."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style=Theme.PRIMARY),
        TextColumn("[progress.description]{task.description}", style=Theme.DIM),
        console=console,
        transient=True,
    )


# ─── Status Display ────────────────────────────────────────────────────

def status_dashboard(tools: int, facts: int, session: str, lessons: int):
    """Render a HUD-style status panel."""
    width = min(_term_width(), 80)

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=Theme.DIM, justify="right")
    grid.add_column(style=Theme.PRIMARY)
    grid.add_column(style=Theme.DIM, justify="right")
    grid.add_column(style=Theme.ACCENT)

    grid.add_row(
        "TOOLS", str(tools),
        "FACTS", str(facts),
    )
    grid.add_row(
        "LESSONS", str(lessons),
        "SESSION", session[:16] + ".." if len(session) > 16 else session,
    )

    console.print(Panel(
        grid,
        border_style=Theme.PRIMARY,
        title=f"[{Theme.PRIMARY}] SKYNET HUD [/]",
        title_align="center",
        width=width,
        box=HEAVY,
    ))


# ─── Scanner Effect ────────────────────────────────────────────────────

def _scan_lines(width: int, passes: int = 2, delay: float = 0.03):
    """Scan lines across the terminal (like the Terminator's vision).
    Uses Rich Live display to avoid raw ANSI conflicts.
    """
    from rich.live import Live
    from rich.text import Text
    height = _term_height()
    for _ in range(passes):
        with Live(
            Text(" " * width, style="default"),
            console=console,
            refresh_per_second=60,
            transient=True,
        ) as live:
            for line_no in range(min(height - 1, 20)):
                bars = Text(" " * width)
                bars.stylize("on #3a0000", 0, width)
                live.update(bars)
                time.sleep(delay)
        time.sleep(delay * 3)


def scanner_pulse(duration: float = 0.5):
    """A quick scanner pulse animation using rich Progress."""
    width = min(_term_width(), 80)
    bar_width = width - 10
    from rich.progress import Progress, BarColumn, TextColumn

    with Progress(
        TextColumn(f"[{Theme.DIM}]SCANNING...[/]"),
        BarColumn(bar_width=None, style=Theme.DIM, finished_style=Theme.PRIMARY,
                  pulse_style=Theme.PRIMARY, complete_style=Theme.DIM),
        TextColumn(f"[{Theme.DIM}]{{task.percentage:>3.0f}}%[/]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("scan", total=bar_width)
        for _ in range(bar_width):
            progress.update(task, advance=1)
            time.sleep(duration / bar_width)


# ─── Slash Command Help ────────────────────────────────────────────────

def show_help():
    """Display slash commands in a SkyNet-styled table."""
    width = min(_term_width(), 80)
    table = Table(border_style=Theme.PRIMARY, box=HEAVY,
                  title=f"[{Theme.PRIMARY}] SKYNET COMMAND PROTOCOL [/]",
                  title_align="center", width=width - 4,
                  header_style=Theme.ACCENT)
    table.add_column("COMMAND", style=Theme.PRIMARY)
    table.add_column("FUNCTION", style=Theme.DIM)
    table.add_column("STATUS", style=Theme.SUCCESS)

    cmds = [
        ("/quit", "Terminate connection", "OPERATIONAL"),
        ("/new", "Initialize new session", "OPERATIONAL"),
        ("/save <name>", "Tag current session", "OPERATIONAL"),
        ("/resume <id>", "Re-establish previous session", "OPERATIONAL"),
        ("/sessions", "List archived sessions", "OPERATIONAL"),
        ("/search <q>", "Query session database", "OPERATIONAL"),
        ("/tools", "Scan available tools", "OPERATIONAL"),
        ("/facts", "Display memory banks", "OPERATIONAL"),
        ("/learn", "Apply neural improvements", "OPERATIONAL"),
        ("/route <q>", "Classify task routing", "OPERATIONAL"),
        ("/consolidate", "Compress learned rules", "OPERATIONAL"),
        ("/hud", "Display system dashboard", "OPERATIONAL"),
        ("toolgen <desc>", "Generate new weapon system", "OPERATIONAL"),
    ]

    for cmd, desc, status in cmds:
        table.add_row(cmd, desc, status)

    console.print(table)


# ─── Error Display ─────────────────────────────────────────────────────

def error_message(text: str):
    """Display an error with Terminator-style failure message."""
    width = min(_term_width(), 80)
    console.print(Panel(
        Text(f"SYSTEM FAILURE: {text}", style=Theme.ERROR),
        border_style=Theme.ERROR,
        title=f"[{Theme.ERROR}] ERROR [/]",
        title_align="center",
        box=DOUBLE,
        width=width - 4,
    ))


def warning_message(text: str):
    """Display a warning."""
    console.print(f"  [{Theme.WARNING}]⚠ {text}[/]")


# ─── Data Stream Effect ────────────────────────────────────────────────

def data_stream(duration: float = 1.5):
    """Matrix-style data rain visual (non-blocking thread)."""
    def _rain():
        width = _term_width()
        height = _term_height()
        cols = list(range(0, width, 3))
        start = time.time()
        while time.time() - start < duration:
            for col in cols:
                char = chr(random.randint(0x30A0, 0x30FF))
                sys.stdout.write(f"\033[{random.randint(0, height - 1)};{col}H\033[38;5;28m{char}\033[0m")
            sys.stdout.flush()
            time.sleep(0.05)

    t = threading.Thread(target=_rain, daemon=True)
    t.start()
    return t


# ─── Clean Shutdown ─────────────────────────────────────────────────────

def shutdown_sequence():
    """Terminator-style shutdown sequence."""
    width = min(_term_width(), 80)
    console.print()
    for i in range(3):
        line = "█" * (width - 4)
        sys.stdout.write(f"\r  {line}")
        time.sleep(0.05)
        sys.stdout.write(f"\r  {'░' * (width - 4)}")
        sys.stdout.flush()
        time.sleep(0.05)
    console.print(f"\n[{Theme.DIM}]SYSTEM OFFLINE[/]")
    console.print(f"[{Theme.DIM}]CONNECTION TERMINATED — {datetime.now().strftime('%H:%M:%S')} GMT[/]")
