import os
import shutil
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

class CheckpointManager:
    """
    Maintains an atomic snapshot stack of workspace changes.
    Allows instant one-click rollback (/undo) if the agent introduces
    a syntax error or unintended modification.
    """

    def __init__(self, workspace_root: str = ".", max_checkpoints: int = 15):
        self.workspace_root = Path(workspace_root).resolve()
        self.checkpoint_dir = self.workspace_root / ".ghost_checkpoints"
        self.max_checkpoints = max_checkpoints
        self.history: List[Dict[str, Any]] = []

    def create_checkpoint(self, description: str, affected_files: Optional[List[str]] = None) -> str:
        """Saves a pre-modification backup of affected files."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time() * 1000)
        checkpoint_id = f"chk_{timestamp}"
        snapshot_dir = self.checkpoint_dir / checkpoint_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        if affected_files:
            for rel_path in affected_files:
                src = self.workspace_root / rel_path
                if src.is_file():
                    dst = snapshot_dir / rel_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    saved_files.append(rel_path)

        entry = {
            "id": checkpoint_id,
            "timestamp": time.strftime("%H:%M:%S"),
            "description": description,
            "files": saved_files,
            "snapshot_dir": str(snapshot_dir)
        }

        self.history.append(entry)

        # Evict older checkpoints past limit
        if len(self.history) > self.max_checkpoints:
            oldest = self.history.pop(0)
            shutil.rmtree(oldest["snapshot_dir"], ignore_errors=True)

        return checkpoint_id

    def rollback_latest(self) -> Dict[str, Any]:
        """Rolls back the most recent checkpoint."""
        if not self.history:
            return {"success": False, "error": "No checkpoints available to undo."}

        last = self.history.pop()
        snapshot_dir = Path(last["snapshot_dir"])
        restored = []

        for rel_path in last["files"]:
            src = snapshot_dir / rel_path
            dst = self.workspace_root / rel_path
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(rel_path)

        # Clean up directory
        shutil.rmtree(snapshot_dir, ignore_errors=True)

        return {
            "success": True,
            "id": last["id"],
            "description": last["description"],
            "restored_files": restored,
            "remaining_checkpoints": len(self.history)
        }

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        return [
            {"id": h["id"], "time": h["timestamp"], "description": h["description"], "files": h["files"]}
            for h in reversed(self.history)
        ]

checkpoint_manager = CheckpointManager()
