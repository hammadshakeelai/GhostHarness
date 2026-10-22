import sys
import os
import asyncio
import argparse
from pathlib import Path

# Add project root to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from core.checkpoint import checkpoint_manager
from core.repo_map import RepoMap

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

    health = await engine.check_health()
    if health["online"]:
        console.print(f"[bold green]✔ Backend Connected:[/bold green] {health['endpoint']} ({health.get('backend', 'Backend')})")
        if health.get("available_models"):
            console.print(f"  Available models: {', '.join(health['available_models'][:3])}")
    else:
        console.print(f"[bold yellow]⚠ Backend Alert:[/bold yellow] {health['status']}")
        console.print("  [dim]Tip: Start LM Studio or llama-server on port 1234 or 8080[/dim]")

    display_telemetry()
    console.print("\n[dim]Commands: /gui (launch web workspace), /undo (revert last edit), /map (show AST tree), /vram, /model <name>, /exit[/dim]\n")

    while True:
        try:
            prompt = console.input("[bold magenta]ghost-coder ❯[/bold magenta] ").strip()
            if not prompt:
                continue

            if prompt in ["/exit", "exit", "quit", ":q"]:
                console.print("[dim]Shutting down GhostHarness session...[/dim]")
                break

            if prompt == "/vram":
                display_telemetry()
                continue

            if prompt == "/undo":
                res = checkpoint_manager.rollback_latest()
                if res.get("success"):
                    console.print(f"[bold green]✔ Restored snapshot:[/bold green] {res['description']}")
                    console.print(f"  Files reverted: {', '.join(res['restored_files'])}")
                else:
                    console.print(f"[bold red]Undo failed:[/bold red] {res.get('error')}")
                continue

            if prompt == "/map":
                rmap = RepoMap(root_dir=agent.workspace_root)
                console.print(Panel(rmap.generate_map(), title="Semantic Codebase Symbol Map", border_style="cyan"))
                continue

            if prompt == "/gui":
                console.print(f"[bold green]Starting Visual Workspace Web GUI on http://127.0.0.1:{settings.web_port}...[/bold green]")
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

            # Claude Code Style Turn Execution
            t = memory_manager.get_hardware_telemetry()
            vram_gb = t['vram_used_mb'] / 1024
            console.print(f"\n[bold cyan]● Thinking[/bold cyan] [dim](qwen-7b | {vram_gb:.1f}/6.0 GB VRAM | zero-spill)[/dim]")
            
            async for evt in agent.process_user_turn(prompt):
                evt_type = evt.get("type")
                if evt_type == "routing":
                    pass
                elif evt_type == "token":
                    console.print(evt["content"], end="")
                elif evt_type == "tool_start":
                    t_name = evt["tool"]
                    args = evt["arguments"]
                    if t_name == "read_file":
                        p = args.get("path", "")
                        s = args.get("start_line", 1)
                        e = args.get("end_line", "end")
                        console.print(f"\n  [bold black on cyan] READ [/bold black on cyan] [bold white]{p}[/bold white]:[dim]{s}-{e}[/dim]")
                    elif t_name == "edit_file":
                        p = args.get("path", "")
                        console.print(f"\n  [bold black on green] EDIT [/bold black on green] [bold white]{p}[/bold white] [dim](surgical patch)[/dim]")
                    elif t_name == "run_terminal":
                        cmd = args.get("command", "")
                        console.print(f"\n  [bold black on yellow] BASH [/bold black on yellow] [bold white]{cmd}[/bold white]")
                    elif t_name == "grep_search":
                        pat = args.get("pattern", "")
                        console.print(f"\n  [bold black on magenta] GREP [/bold black on magenta] [bold white]{pat}[/bold white]")
                    else:
                        console.print(f"\n  [bold black on blue] TOOL [/bold black on blue] [bold white]{t_name}[/bold white]({args})")
                elif evt_type == "tool_end":
                    res = evt["result"]
                    if evt["tool"] == "edit_file" and "diff" in res:
                        console.print(Panel(
                            Syntax(res["diff"], "diff", theme="monokai", line_numbers=True),
                            title=f"[bold green]Patch Applied: {evt['arguments'].get('path')}[/bold green]",
                            border_style="green",
                            padding=(0, 1)
                        ))
                    elif evt["tool"] == "run_terminal":
                        stdout = res.get("stdout", "").strip()
                        exit_c = res.get("exit_code", 0)
                        status_str = f"[green]exit {exit_c}[/green]" if exit_c == 0 else f"[red]exit {exit_c}[/red]"
                        if stdout:
                            preview = "\n".join(stdout.splitlines()[:6])
                            console.print(f"    └─ {status_str}: [dim]{preview}[/dim]")
                        else:
                            console.print(f"    └─ {status_str}")
                    elif not res.get("success", False):
                        console.print(f"    [bold red]Error:[/bold red] {res.get('error')}")
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
