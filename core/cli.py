import sys
import os
import asyncio
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from core.config import settings
from core.agent import Agent
from core.memory_manager import memory_manager
from core.dynamic_router import model_router
from core.engine import InferenceEngine

console = Console()

def print_banner():
    banner = r"""
   ________                  __  __                                
  / ____/ /_  ____  _____/ /_/ / /___ _____  ____  ___  __________
 / / __/ __ \/ __ \/ ___/ __/ /_/ / __ `/ __ \/ __ \/ _ \/ ___/ ___/
/ /_/ / / / / /_/ (__  ) /_/ __  / /_/ / / / / / / /  __/ /  (__  ) 
\____/_/ /_/\____/____/\__/_/ /_/\__,_/_/ /_/_/ /_/\___/_/  /____/  
    [Sovereign Local Agent Harness | Zero Admin | 6GB VRAM Guard]
    """
    console.print(f"[bold cyan]{banner}[/bold cyan]")

def display_telemetry():
    t = memory_manager.get_hardware_telemetry()
    table = Table(title="Hardware Budget Telemetry", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Usage", justify="right")
    table.add_column("Limit / Total", justify="right")
    table.add_column("Status", style="green")

    vram_color = "green" if t["vram_percent"] < 80 else ("yellow" if t["vram_percent"] < 95 else "red")
    table.add_row(
        f"Discrete VRAM ({t['gpu_name']})",
        f"{t['vram_used_mb'] / 1024:.2f} GB ({t['vram_percent']}%)",
        f"{t['vram_total_mb'] / 1024:.2f} GB",
        f"[{vram_color}]{t['status_message']}[/{vram_color}]"
    )
    table.add_row(
        "System RAM",
        f"{t['ram_used_mb'] / 1024:.2f} GB ({t['ram_percent']}%)",
        f"{t['ram_total_mb'] / 1024:.2f} GB",
        "[green]Available for offload[/green]"
    )
    console.print(table)

async def run_tui():
    print_banner()
    agent = Agent()
    engine = InferenceEngine()

    # Backend verification
    health = await engine.check_health()
    if health["online"]:
        console.print(f"[bold green]✔ Backend Connected:[/bold green] {health['endpoint']}")
        console.print(f"  Available models: {', '.join(health['available_models'][:3])}")
    else:
        console.print(f"[bold yellow]⚠ Backend Alert:[/bold yellow] {health['status']}")
        console.print("  [dim]Tip: Start LM Studio or llama-server on port 1234[/dim]")

    display_telemetry()
    console.print("\n[dim]Commands: /gui (launch visual dashboard), /vram (check memory), /model <name>, /exit[/dim]\n")

    while True:
        try:
            prompt = console.input("[bold magenta]ghost-coder>[/bold magenta] ").strip()
            if not prompt:
                continue

            if prompt in ["/exit", "exit", "quit", ":q"]:
                console.print("[dim]Shutting down GhostHarness session...[/dim]")
                break

            if prompt == "/vram":
                display_telemetry()
                continue

            if prompt == "/gui":
                console.print("[bold green]Starting Visual Workspace Web GUI on http://127.0.0.1:8765...[/bold green]")
                from web.server import start_server
                start_server(port=settings.web_port)
                continue

            if prompt.startswith("/model"):
                parts = prompt.split()
                if len(parts) > 1:
                    model_router.set_override(parts[1])
                    console.print(f"[bold green]Model override set to: {parts[1]}[/bold green]")
                else:
                    model_router.set_override(None)
                    console.print("[bold green]Dynamic auto-switching re-enabled.[/bold green]")
                continue

            console.print(f"\n[dim]Analyzing task & routing...[/dim]")
            async for evt in agent.process_user_turn(prompt):
                evt_type = evt.get("type")
                if evt_type == "routing":
                    console.print(f"[bold cyan]⚡ Engine Selected:[/bold cyan] {evt['model']} ({evt['tier'].upper()}) - {evt['reason']}")
                elif evt_type == "token":
                    console.print(evt["content"], end="")
                elif evt_type == "tool_start":
                    console.print(f"\n[bold yellow]⚙ Tool Call:[/bold yellow] {evt['tool']}({evt['arguments']})")
                elif evt_type == "tool_end":
                    res = evt["result"]
                    if evt["tool"] == "edit_file" and "diff" in res:
                        console.print("\n[bold green]Generated Surgical Code Diff:[/bold green]")
                        console.print(Syntax(res["diff"], "diff", theme="monokai", line_numbers=True))
                    elif not res.get("success", False):
                        console.print(f"[bold red]Tool Result Error:[/bold red] {res.get('error')}")
            console.print("\n")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session closed.[/dim]")
            break

def main():
    parser = argparse.ArgumentParser(description="GhostHarness Sovereign Agent")
    parser.add_argument("--gui", action="store_true", help="Launch Visual Web Workspace")
    parser.add_argument("--port", type=int, default=8765, help="Web server port")
    args = parser.parse_args()

    if args.gui:
        from web.server import start_server
        start_server(port=args.port)
    else:
        asyncio.run(run_tui())

if __name__ == "__main__":
    main()
