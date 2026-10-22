import asyncio
import os
import shlex
from pathlib import Path
from typing import Dict, Any

async def run_terminal(command: str, cwd: str = ".", timeout_seconds: int = 60) -> Dict[str, Any]:
    """Executes a command safely in user-space without administrator privileges."""
    try:
        work_dir = Path(cwd).resolve()
        if not work_dir.exists():
            work_dir = Path.cwd()

        # Prevent destructive accidental commands like rm -rf /
        dangerous_patterns = ["rm -rf /", ":(){ :|:& };:", "mkfs", "dd if="]
        for pattern in dangerous_patterns:
            if pattern in command:
                return {
                    "success": False,
                    "error": f"Command rejected by safety guard: dangerous pattern detected ('{pattern}')"
                }

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir)
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": f"Execution timed out after {timeout_seconds} seconds."
            }

        stdout_str = stdout_data.decode("utf-8", errors="replace")
        stderr_str = stderr_data.decode("utf-8", errors="replace")

        return {
            "success": process.returncode == 0,
            "exit_code": process.returncode,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "cwd": str(work_dir)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
