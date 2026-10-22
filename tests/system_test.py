import os
import sys
import time
import shutil
import tempfile
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Graceful Rich import with ANSI fallback
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

def color(text: str, code: str) -> str:
    codes = {
        "cyan": "\033[96m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m"
    }
    return f"{codes.get(code, '')}{text}{codes['reset']}"

class SystemDiagnosticSuite:
    def __init__(self):
        self.results = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ghost_test_"))

    def record(self, category: str, test_name: str, passed: bool, details: str, severity: str = "error"):
        self.results.append({
            "category": category,
            "test": test_name,
            "passed": passed,
            "details": details,
            "severity": severity
        })

    def run_all(self):
        if HAS_RICH and console:
            console.print(Panel.fit(
                "[bold cyan]⚡ GhostHarness System-Wide Diagnostic & Verification Suite ⚡[/bold cyan]\n"
                "[dim]Testing environment, hardware telemetry, tool sandbox, AST repomap, and zero-spill compliance[/dim]",
                border_style="cyan"
            ))
        else:
            print("=" * 70)
            print(color("⚡ GhostHarness System-Wide Diagnostic & Verification Suite ⚡", "cyan"))
            print(color("Testing environment, hardware telemetry, tool sandbox, AST repomap, and zero-spill compliance", "dim"))
            print("=" * 70)

        self.test_environment()
        self.test_hardware_telemetry()
        self.test_repomap()
        self.test_filesystem_and_fuzzy_patcher()
        self.test_checkpoint_and_rollback()
        self.test_terminal_sandbox()
        self.test_dynamic_router()
        self.test_backend_connectivity()
        self.test_web_api_routes()
        self.test_offline_model_assets()

        self.cleanup()
        self.render_report()

    def test_environment(self):
        v = sys.version_info
        py_ver = f"{v.major}.{v.minor}.{v.micro}"
        if v.major == 3 and v.minor >= 10:
            self.record("Environment", "Python Version", True, f"Python {py_ver} (>= 3.10 required)")
        else:
            self.record("Environment", "Python Version", False, f"Python {py_ver} is unsupported. Python 3.10+ required.")

        is_root = False
        try:
            is_root = (os.geteuid() == 0)
        except AttributeError:
            pass

        if not is_root:
            self.record("Environment", "Zero-Admin Privilege Check", True, "Running as standard unprivileged user (No root / sudo required)")
        else:
            self.record("Environment", "Zero-Admin Privilege Check", False, "Running as root! Recommended to run as normal user for safety", "warning")

        test_file = PROJECT_ROOT / ".write_test_tmp"
        try:
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            self.record("Environment", "Workspace Writable", True, "Current folder is writable in user-space without elevation")
        except Exception as e:
            self.record("Environment", "Workspace Writable", False, f"Permission denied writing to workspace: {e}")

    def test_hardware_telemetry(self):
        try:
            from core.memory_manager import memory_manager
            tele = memory_manager.get_hardware_telemetry()

            vram_mb = tele["vram_total_mb"]
            gpu_name = tele["gpu_name"]
            if vram_mb >= 5000:
                self.record("Hardware", "VRAM Capacity (6GB Target)", True, f"{gpu_name}: {vram_mb/1024:.1f} GB total VRAM")
            elif vram_mb > 0:
                self.record("Hardware", "VRAM Capacity (6GB Target)", True, f"{gpu_name}: {vram_mb/1024:.1f} GB (Sub-6GB, smaller models advised)", "warning")
            else:
                self.record("Hardware", "GPU Detection", True, "Host GPU / Integrated VRAM detected (Inference via CPU/shared memory)", "warning")

            ram_gb = tele["ram_total_mb"] / 1024
            if ram_gb >= 16:
                self.record("Hardware", "System RAM Check", True, f"{ram_gb:.1f} GB System RAM available (Sufficient for hybrid offloading)")
            elif ram_gb >= 6:
                self.record("Hardware", "System RAM Check", True, f"{ram_gb:.1f} GB System RAM (Adequate for 7B pure VRAM tier; 16-32GB advised for 14B/32B)", "warning")
            else:
                self.record("Hardware", "System RAM Check", False, f"{ram_gb:.1f} GB System RAM (< 6GB critical memory constraint)", "error")

            self.record("Hardware", "Zero-Spill Guard", not tele["spill_risk"], tele["status_message"])
        except Exception as e:
            self.record("Hardware", "Telemetry Module", False, f"Error inspecting hardware: {e}")

    def test_repomap(self):
        try:
            from core.repo_map import RepoMap
            rmap = RepoMap(root_dir=str(PROJECT_ROOT))
            rendered = rmap.generate_map()
            if "core/agent.py" in rendered and "class Agent" in rendered:
                self.record("Agent Core", "AST Semantic RepoMap", True, f"Generated AST symbol tree ({len(rendered)} chars, token budgeted)")
            else:
                self.record("Agent Core", "AST Semantic RepoMap", False, "RepoMap failed to extract symbols from codebase")
        except Exception as e:
            self.record("Agent Core", "AST Semantic RepoMap", False, f"Error generating repomap: {e}")

    def test_filesystem_and_fuzzy_patcher(self):
        try:
            from tools.filesystem import read_file, write_file, edit_file
            test_file = self.temp_dir / "sample.py"
            test_rel = str(test_file.relative_to(self.temp_dir))

            sample_code = "def calculate_sum(a, b):\n    # add two numbers\n    return a + b\n"
            asyncio.run(write_file(test_rel, sample_code, root=str(self.temp_dir)))
            if test_file.is_file() and test_file.read_text() == sample_code:
                self.record("Tools", "Filesystem write_file", True, "Successfully created file on disk")
            else:
                self.record("Tools", "Filesystem write_file", False, "Failed to create file")

            res_read = asyncio.run(read_file(test_rel, start_line=1, end_line=2, root=str(self.temp_dir)))
            if res_read.get("success") and "calculate_sum" in res_read.get("content", ""):
                self.record("Tools", "Filesystem read_file", True, "Successfully read line-sliced content")
            else:
                self.record("Tools", "Filesystem read_file", False, f"Failed read: {res_read.get('error')}")

            fuzzy_target = "def calculate_sum(a, b):\n   # add two numbers\n   return a + b"
            replacement = "def calculate_sum(a, b, c=0):\n    # add three numbers\n    return a + b + c"
            res_edit = asyncio.run(edit_file(test_rel, fuzzy_target, replacement, root=str(self.temp_dir)))

            if res_edit.get("success") and "diff" in res_edit:
                self.record("Tools", "Fuzzy Edit Matcher", True, "Surgically patched file despite whitespace difference via 85% sequence matcher")
            else:
                self.record("Tools", "Fuzzy Edit Matcher", False, f"Fuzzy matching failed: {res_edit.get('error')}")
        except Exception as e:
            self.record("Tools", "Filesystem Tools", False, f"Error: {e}")

    def test_checkpoint_and_rollback(self):
        try:
            from core.checkpoint import checkpoint_manager
            checkpoint_manager.workspace_root = self.temp_dir
            checkpoint_manager.checkpoint_dir = self.temp_dir / ".ghost_checkpoints"

            target_file = self.temp_dir / "rollback_test.txt"
            target_file.write_text("INITIAL_STATE_12345", encoding="utf-8")

            checkpoint_manager.create_checkpoint("Pre-modification checkpoint", ["rollback_test.txt"])
            target_file.write_text("CORRUPTED_HALLUCINATED_STATE", encoding="utf-8")

            undo_res = checkpoint_manager.rollback_latest()
            final_content = target_file.read_text(encoding="utf-8")

            if undo_res.get("success") and final_content == "INITIAL_STATE_12345":
                self.record("Safety", "Checkpoint & Rollback Engine", True, "Successfully rolled back corrupted file state to pristine snapshot")
            else:
                self.record("Safety", "Checkpoint & Rollback Engine", False, f"Rollback failed: {undo_res}")
        except Exception as e:
            self.record("Safety", "Checkpoint Engine", False, f"Error: {e}")

    def test_terminal_sandbox(self):
        try:
            from tools.terminal import run_terminal

            res = asyncio.run(run_terminal("echo 'GhostHarness Sandbox OK'", cwd=str(self.temp_dir)))
            if res.get("success") and "GhostHarness Sandbox OK" in res.get("stdout", ""):
                self.record("Tools", "Terminal Execution", True, "Executed user-space command successfully")
            else:
                self.record("Tools", "Terminal Execution", False, f"Terminal command failed: {res.get('error')}")

            res_danger = asyncio.run(run_terminal("rm -rf /", cwd=str(self.temp_dir)))
            if not res_danger.get("success") and "safety guard" in res_danger.get("error", "").lower():
                self.record("Safety", "Dangerous Command Filter", True, "Intercepted and neutralized malicious pattern ('rm -rf /')")
            else:
                self.record("Safety", "Dangerous Command Filter", False, "Failed to block dangerous command!")
        except Exception as e:
            self.record("Tools", "Terminal Sandbox", False, f"Error: {e}")

    def test_dynamic_router(self):
        try:
            from core.dynamic_router import model_router

            fast_dec = model_router.select_model("read line 5 of main.py and grep for auth tokens", [])
            is_fast_pass = (fast_dec["tier"] == "fast")

            heavy_dec = model_router.select_model("perform a full architecture refactoring with new concurrency model", [])
            is_heavy_pass = (heavy_dec["tier"] == "heavy")

            if is_fast_pass and is_heavy_pass:
                self.record("Engine", "Dynamic Model Router", True, "Correctly classified tactical operations to 7B and architecture to 14B")
            else:
                self.record("Engine", "Dynamic Model Router", False, f"Routing misclassification: Fast={fast_dec['tier']}, Heavy={heavy_dec['tier']}")
        except Exception as e:
            self.record("Engine", "Dynamic Model Router", False, f"Error: {e}")

    def test_backend_connectivity(self):
        try:
            from core.engine import InferenceEngine
            engine = InferenceEngine()
            health = asyncio.run(engine.check_health())

            if health.get("online"):
                self.record("Backend", "Local LLM Backend Discovery", True, f"Active server found: {health.get('backend')} at {health.get('endpoint')}")
            else:
                self.record("Backend", "Local LLM Backend Discovery", True, "No server currently running on port 1234/8080 (Start LM Studio or llama-server)", "warning")
        except Exception as e:
            self.record("Backend", "Local LLM Backend Discovery", False, f"Error probing backend: {e}")

    def test_web_api_routes(self):
        try:
            from web.server import app
            routes = [r.path for r in app.routes]
            expected = ["/api/telemetry", "/api/health", "/api/plugins", "/api/repomap", "/api/checkpoints", "/api/undo", "/api/chat"]
            missing = [exp for exp in expected if exp not in routes]

            if not missing:
                self.record("Web GUI", "FastAPI Route Verification", True, f"All {len(expected)} visual workspace API endpoints verified")
            else:
                self.record("Web GUI", "FastAPI Route Verification", False, f"Missing routes: {missing}")
        except Exception as e:
            self.record("Web GUI", "FastAPI Route Verification", False, f"Error loading server: {e}")

    def test_offline_model_assets(self):
        models_dir = PROJECT_ROOT / "models"
        models = list(models_dir.glob("*.gguf")) if models_dir.is_dir() else []

        if models:
            names = [f"{m.name} ({m.stat().st_size / (1024**3):.2f} GB)" for m in models]
            self.record("Offline Assets", "GGUF Models in models/", True, f"Found {len(models)} model(s): {', '.join(names)}")
        else:
            self.record("Offline Assets", "GGUF Models in models/", True, "No GGUF models in models/ directory yet (Download in progress)", "warning")

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def render_report(self):
        passed_count = 0
        warning_count = 0
        error_count = 0

        if HAS_RICH and console:
            table = Table(title="Diagnostic Results Breakdown", border_style="cyan")
            table.add_column("Category", style="bold cyan")
            table.add_column("Test Item", style="bold")
            table.add_column("Status", justify="center")
            table.add_column("Details", style="dim")

            for r in self.results:
                if r["passed"]:
                    if r["severity"] == "warning":
                        status_text = "[bold yellow]⚠ WARN[/bold yellow]"
                        warning_count += 1
                    else:
                        status_text = "[bold green]✔ PASS[/bold green]"
                        passed_count += 1
                else:
                    status_text = "[bold red]✖ FAIL[/bold red]"
                    error_count += 1
                table.add_row(r["category"], r["test"], status_text, r["details"])

            console.print(table)
            total = len(self.results)
            console.print(f"\n[bold]Diagnostic Summary:[/bold] {passed_count}/{total} Passed | {warning_count} Warnings | {error_count} Errors")

            if error_count == 0:
                console.print("[bold green]🚀 SYSTEM VERIFICATION COMPLETE: Ready for deployment on university lab PCs.[/bold green]\n")
            else:
                console.print("[bold red]⚠ Fix the failed items before deploying to air-gapped machines.[/bold red]\n")
        else:
            # Fallback pure ANSI terminal table
            print(f"{'Category':<15} | {'Test Item':<30} | {'Status':<10} | {'Details'}")
            print("-" * 80)
            for r in self.results:
                if r["passed"]:
                    if r["severity"] == "warning":
                        st = color("⚠ WARN", "yellow")
                        warning_count += 1
                    else:
                        st = color("✔ PASS", "green")
                        passed_count += 1
                else:
                    st = color("✖ FAIL", "red")
                    error_count += 1
                print(f"{r['category']:<15} | {r['test']:<30} | {st:<19} | {r['details']}")

            total = len(self.results)
            print("-" * 80)
            print(f"Summary: {passed_count}/{total} Passed | {warning_count} Warnings | {error_count} Errors")
            if error_count == 0:
                print(color("\n🚀 SYSTEM VERIFICATION COMPLETE: Ready for deployment on university lab PCs.\n", "green"))
            else:
                print(color("\n⚠ Fix the failed items before deploying.\n", "red"))

if __name__ == "__main__":
    suite = SystemDiagnosticSuite()
    suite.run_all()
