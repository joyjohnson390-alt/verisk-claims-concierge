"""
Verisk Property Estimating Network — Claims Concierge AI
Rich-based interactive terminal demo runner.
"""

import sys
import time
import threading
import requests
from typing import Optional, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich.prompt import Prompt
from rich import print as rprint

console = Console()

# ---------------------------------------------------------------------------
# Persona definitions
# ---------------------------------------------------------------------------
PERSONAS = {
    "claimant": {
        "label": "Claimant",
        "name": "Robert Chen",
        "user_id": "CLM-001",
        "style": "bold cyan",
    },
    "contractor": {
        "label": "Contractor",
        "name": "Jake Morales",
        "user_id": "CON-001",
        "style": "bold yellow",
    },
    "adjuster": {
        "label": "Adjuster",
        "name": "Maria Santos",
        "user_id": "ADJ-001",
        "style": "bold magenta",
    },
}

WEATHER_API_URL = "http://localhost:8001"

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
state = {
    "persona": "claimant",
    "user_id": "CLM-001",
    "messages": [],
    "claim_id": None,
    "claim_data": None,
    "weather_data": None,
    "estimate_data": None,
    "weather_available": True,
    "write_payload": None,
    "awaiting_confirmation": False,
    "error_message": None,
    "intent": None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _weather_status() -> tuple[str, str]:
    """Return (indicator, label) for current weather API health."""
    try:
        resp = requests.get(f"{WEATHER_API_URL}/admin/status", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("enabled", True):
                return "[green]●[/green]", "Weather API: UP"
            else:
                return "[red]●[/red]", "Weather API: DOWN (simulated)"
    except Exception:
        pass
    return "[red]●[/red]", "Weather API: UNREACHABLE"


def _print_header():
    """Print the top branding panel."""
    title = Text("VERISK Property Estimating Network", style="bold white")
    subtitle = Text("Claims Concierge AI  |  Technical Demo", style="dim white")
    header_text = Text.assemble(title, "\n", subtitle)
    console.print(
        Panel(
            header_text,
            border_style="bright_blue",
            padding=(0, 2),
        )
    )


def _print_status_bar():
    """Print current persona + API health status."""
    p = PERSONAS.get(state["persona"], PERSONAS["claimant"])
    indicator, label = _weather_status()

    status = Table.grid(padding=(0, 2))
    status.add_column(no_wrap=True)
    status.add_column(no_wrap=True)
    status.add_column(no_wrap=True)
    status.add_row(
        f"[{p['style']}]Persona:[/{p['style']}] [{p['style']}]{p['label']} — {p['name']} ({p['user_id']})[/{p['style']}]",
        f"{indicator} {label}",
        "[dim]Type :help for commands[/dim]",
    )
    console.print(Panel(status, border_style="dim", padding=(0, 1)))


def _simulate_typing(text: str, delay: float = 0.03):
    """Print text with a typing animation then newline."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _print_user_bubble(text: str):
    p = PERSONAS.get(state["persona"], PERSONAS["claimant"])
    console.print(
        Panel(
            f"[{p['style']}]{text}[/{p['style']}]",
            title=f"[{p['style']}]{p['name']} ({p['label']})[/{p['style']}]",
            title_align="left",
            border_style="blue",
            padding=(0, 2),
        )
    )


def _print_ai_bubble(text: str, sources: Optional[List[str]] = None):
    console.print(
        Panel(
            f"[green]{text}[/green]",
            title="[bold green]Claims Concierge AI[/bold green]",
            title_align="left",
            border_style="green",
            padding=(0, 2),
        )
    )
    if sources:
        src_str = "  ".join(f"[dim]{s}[/dim]" for s in sources)
        console.print(f"  [dim]Sources: {src_str}[/dim]")


def _print_error(msg: str):
    console.print(Panel(f"[red]{msg}[/red]", border_style="red", title="[red]Error[/red]"))


def _print_info(msg: str):
    console.print(f"[dim cyan]{msg}[/dim cyan]")


def _build_state_dict(user_message: str) -> dict:
    """Build the state dict to pass to run_turn."""
    from copy import deepcopy

    s = deepcopy(state)
    s["messages"] = state["messages"] + [{"role": "user", "content": user_message}]
    return s


def _apply_result(result: dict):
    """Merge result back into global state."""
    for key in (
        "messages",
        "claim_id",
        "claim_data",
        "weather_data",
        "estimate_data",
        "weather_available",
        "write_payload",
        "awaiting_confirmation",
        "error_message",
        "intent",
    ):
        if key in result:
            state[key] = result[key]


def _send_message(user_message: str, auto_type: bool = False):
    """Send a message through the agent and display response."""
    if auto_type:
        console.print()
        p = PERSONAS.get(state["persona"], PERSONAS["claimant"])
        console.print(f"  [{p['style']}]{p['name']}:[/{p['style']}] ", end="")
        _simulate_typing(user_message)
        _print_user_bubble(user_message)
    else:
        _print_user_bubble(user_message)

    console.print("[dim]  Thinking…[/dim]")

    try:
        from agent.graph import run_turn

        state_dict = _build_state_dict(user_message)
        result = run_turn(state_dict)
        _apply_result(result)

        # Extract the last AI message (LangChain AIMessage has type="ai")
        ai_reply = None
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
                is_ai = role in ("assistant", "ai")
            else:
                msg_type = getattr(msg, "type", "") or getattr(msg, "role", "")
                content = getattr(msg, "content", "")
                is_ai = msg_type in ("ai", "assistant")
            if is_ai and content:
                ai_reply = content if isinstance(content, str) else str(content)
                break

        if ai_reply:
            sources = []
            if result.get("claim_data"):
                sources.append("Data 360")
            if result.get("weather_data"):
                sources.append("Weather API")
            if result.get("estimate_data"):
                sources.append("PES/AccuLynx")
            _print_ai_bubble(ai_reply, sources if sources else None)
        else:
            _print_error("No response received from the agent.")

    except ImportError:
        _print_error("agent.graph module not found. Ensure the agent package is installed.")
    except Exception as exc:
        _print_error(f"Agent error: {exc}")

    console.print()


# ---------------------------------------------------------------------------
# Weather API control
# ---------------------------------------------------------------------------

def _toggle_weather():
    """POST to weather mock API to toggle availability."""
    try:
        resp = requests.post(f"{WEATHER_API_URL}/admin/toggle", timeout=3)
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}


def cmd_kill_weather():
    indicator, label = _weather_status()
    if "UP" in label:
        result = _toggle_weather()
        console.print(f"[red]Weather API toggled → {result}[/red]")
    else:
        console.print("[yellow]Weather API is already down.[/yellow]")


def cmd_restore_weather():
    indicator, label = _weather_status()
    if "DOWN" in label or "UNREACHABLE" in label:
        result = _toggle_weather()
        console.print(f"[green]Weather API toggled → {result}[/green]")
    else:
        console.print("[yellow]Weather API is already up.[/yellow]")


def cmd_status():
    indicator, label = _weather_status()
    console.print(f"  {indicator} {label}")


# ---------------------------------------------------------------------------
# Persona switching
# ---------------------------------------------------------------------------

def cmd_persona(args: List[str]):
    """Switch persona: :persona claimant CLM-001"""
    if not args:
        console.print("[yellow]Usage: :persona <claimant|contractor|adjuster> <user_id>[/yellow]")
        return
    role = args[0].lower()
    if role not in PERSONAS:
        console.print(f"[red]Unknown persona '{role}'. Choose: claimant, contractor, adjuster[/red]")
        return
    user_id = args[1] if len(args) > 1 else PERSONAS[role]["user_id"]
    state["persona"] = role
    state["user_id"] = user_id
    state["messages"] = []
    state["claim_id"] = None
    p = PERSONAS[role]
    console.print(
        f"[{p['style']}]Switched to {p['label']}: {p['name']} ({user_id})[/{p['style']}]"
    )


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

def demo1():
    """Demo 1: Claimant checks claim status."""
    console.print(Rule("[bold cyan]DEMO 1 — Claimant: Claim Status Inquiry[/bold cyan]"))
    console.print(
        Panel(
            "[dim]Robert Chen (CLM-001) asks for a full status update on his property claim,\n"
            "including damage assessment, repair progress, and linked weather event.[/dim]",
            border_style="dim cyan",
        )
    )

    state["persona"] = "claimant"
    state["user_id"] = "CLM-001"
    state["messages"] = []
    state["claim_id"] = None

    _print_status_bar()

    message = (
        "What's the current status of my claim CLM-2024-0891? "
        "I want to know everything — the damage assessment, the repair progress, "
        "and whether there was a weather event linked to my claim."
    )
    _send_message(message, auto_type=True)


def demo2():
    """Demo 2: Contractor submits work order update."""
    console.print(Rule("[bold yellow]DEMO 2 — Contractor: Work Order Update[/bold yellow]"))
    console.print(
        Panel(
            "[dim]Jake Morales (CON-001) submits a progress update on work order WO-2024-0891-A.\n"
            "Demonstrates write-path: intent detection → confirmation → AccuLynx write.[/dim]",
            border_style="dim yellow",
        )
    )

    state["persona"] = "contractor"
    state["user_id"] = "CON-001"
    state["messages"] = []
    state["claim_id"] = None

    _print_status_bar()

    message = (
        "I need to submit an update on work order WO-2024-0891-A. "
        "Roof replacement is 80% complete — we finished installing new shingles on the front section. "
        "On track to complete by end of this week."
    )
    _send_message(message, auto_type=True)

    # If agent is awaiting confirmation, auto-confirm
    if state.get("awaiting_confirmation"):
        time.sleep(1.5)
        console.print("[dim]  (Auto-confirming for demo…)[/dim]")
        _send_message("Yes, please go ahead and submit that update.", auto_type=True)


def demo3():
    """Demo 3: Adjuster book review + graceful weather API degradation."""
    console.print(Rule("[bold magenta]DEMO 3 — Adjuster: Book Review + API Resilience[/bold magenta]"))
    console.print(
        Panel(
            "[dim]Maria Santos (ADJ-001) first reviews her book of claims.\n"
            "Then the weather API is killed mid-demo to demonstrate graceful degradation.[/dim]",
            border_style="dim magenta",
        )
    )

    state["persona"] = "adjuster"
    state["user_id"] = "ADJ-001"
    state["messages"] = []
    state["claim_id"] = None

    _print_status_bar()

    # Step 1
    _send_message("Show me all the claims in my current book.", auto_type=True)

    # Step 2 — prompt presenter to kill weather
    console.print()
    console.print(
        Panel(
            "[bold red]PRESENTER ACTION REQUIRED[/bold red]\n\n"
            "Type  [bold white]:kill-weather[/bold white]  and press Enter\n"
            "to simulate a weather API outage, then press Enter again to continue.",
            border_style="red",
            title="[red]Demo Control[/red]",
        )
    )
    input("  Press Enter when ready to continue with weather API down… ")
    console.print()

    # Step 3 — full status with weather down
    _send_message(
        "Give me a full status report on claim CLM-2024-1023, including weather data.",
        auto_type=True,
    )

    indicator, label = _weather_status()
    console.print(
        Panel(
            f"{indicator} {label}\n\n"
            "[dim]Notice: the AI surfaced claim data successfully while noting\n"
            "that weather information is temporarily unavailable.[/dim]",
            border_style="dim",
            title="[dim]Graceful Degradation[/dim]",
        )
    )


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

def _print_help():
    table = Table(title="Available Commands", border_style="dim", show_header=True)
    table.add_column("Command", style="bold cyan", no_wrap=True)
    table.add_column("Description")
    table.add_row(":demo1", "Run Demo 1 — Claimant checks claim status")
    table.add_row(":demo2", "Run Demo 2 — Contractor submits work order update")
    table.add_row(":demo3", "Run Demo 3 — Adjuster book + API outage (interactive)")
    table.add_row(":persona claimant CLM-001", "Switch to claimant persona")
    table.add_row(":persona contractor CON-001", "Switch to contractor persona")
    table.add_row(":persona adjuster ADJ-001", "Switch to adjuster persona")
    table.add_row(":kill-weather", "Toggle weather API OFF (simulate outage)")
    table.add_row(":restore-weather", "Toggle weather API back ON")
    table.add_row(":status", "Show current weather API health")
    table.add_row(":clear", "Clear conversation history")
    table.add_row(":help", "Show this help message")
    table.add_row(":quit / :exit", "Exit the demo")
    console.print(table)


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def run_demo():
    """Main entry point — launches the interactive demo REPL."""
    console.clear()
    _print_header()
    _print_status_bar()
    _print_help()
    console.print()

    while True:
        try:
            _print_status_bar()
            raw = console.input("[bold white]> [/bold white]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting demo.[/dim]")
            break

        if not raw:
            continue

        if raw.startswith(":"):
            parts = raw[1:].split()
            cmd = parts[0].lower() if parts else ""
            args = parts[1:]

            if cmd in ("quit", "exit", "q"):
                console.print("[dim]Goodbye.[/dim]")
                break
            elif cmd == "demo1":
                demo1()
            elif cmd == "demo2":
                demo2()
            elif cmd == "demo3":
                demo3()
            elif cmd == "persona":
                cmd_persona(args)
            elif cmd == "kill-weather":
                cmd_kill_weather()
            elif cmd == "restore-weather":
                cmd_restore_weather()
            elif cmd == "status":
                cmd_status()
            elif cmd == "clear":
                state["messages"] = []
                state["claim_id"] = None
                console.clear()
                _print_header()
                _print_info("Conversation cleared.")
            elif cmd == "help":
                _print_help()
            else:
                console.print(f"[red]Unknown command: :{cmd}[/red]  Type :help for options.")
        else:
            _send_message(raw)
