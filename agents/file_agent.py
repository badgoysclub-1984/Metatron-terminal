#!/usr/bin/env python3
"""
METATRON OS — agents/file_agent.py
FileAgent (charge = 0)
Handles read, write, delete, list, mkdir operations.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.base_agent import Z9Agent


class FileAgent(Z9Agent):
    """Z9 agent with charge 0: filesystem operations."""

    def __init__(self):
        super().__init__(name="FileAgent", charge=0)

    def execute(
        self,
        path: str,
        operation: str = "read",
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform a filesystem operation.

        Operations: read | write | delete | list | mkdir | stat | copy | move
        """
        try:
            p = Path(path).expanduser().resolve()

            if operation == "read":
                return self._read(p)
            elif operation == "write":
                return self._write(p, content or "")
            elif operation == "delete":
                return self._delete(p)
            elif operation in ("list", "ls"):
                return self._list(p)
            elif operation == "mkdir":
                return self._mkdir(p)
            elif operation == "stat":
                return self._stat(p)
            elif operation == "copy":
                dest = Path(content).expanduser().resolve() if content else None
                return self._copy(p, dest)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except PermissionError as exc:
            return {"success": False, "error": f"Permission denied: {exc}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── private helpers ────────────────────────────────────────

    def _read(self, p: Path) -> Dict[str, Any]:
        if p.is_file():
            try:
                return {"success": True, "content": p.read_text(errors="replace"), "path": str(p)}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        if p.is_dir():
            return self._list(p)
        return {"success": False, "error": f"Path not found: {p}"}

    def _write(self, p: Path, content: str) -> Dict[str, Any]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"success": True, "written": str(p), "bytes": len(content.encode())}

    def _delete(self, p: Path) -> Dict[str, Any]:
        if p.is_file():
            p.unlink()
            return {"success": True, "deleted": str(p)}
        if p.is_dir():
            shutil.rmtree(p)
            return {"success": True, "deleted": str(p), "type": "directory"}
        return {"success": False, "error": f"Not found: {p}"}

    def _list(self, p: Path) -> Dict[str, Any]:
        if not p.is_dir():
            return {"success": False, "error": f"Not a directory: {p}"}
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
        listing = []
        for e in entries[:50]:
            listing.append({
                "name": e.name,
                "type": "dir" if e.is_dir() else "file",
                "size": e.stat().st_size if e.is_file() else None,
            })
        return {"success": True, "listing": listing, "path": str(p), "count": len(listing)}

    def _mkdir(self, p: Path) -> Dict[str, Any]:
        p.mkdir(parents=True, exist_ok=True)
        return {"success": True, "created_dir": str(p)}

    def _stat(self, p: Path) -> Dict[str, Any]:
        if not p.exists():
            return {"success": False, "error": f"Not found: {p}"}
        s = p.stat()
        return {
            "success": True,
            "path": str(p),
            "size": s.st_size,
            "modified": s.st_mtime,
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
        }

    def _copy(self, src: Path, dst: Optional[Path]) -> Dict[str, Any]:
        if dst is None:
            return {"success": False, "error": "Destination not specified"}
        if src.is_file():
            shutil.copy2(src, dst)
        elif src.is_dir():
            shutil.copytree(src, dst)
        else:
            return {"success": False, "error": f"Source not found: {src}"}
        return {"success": True, "copied": str(src), "to": str(dst)}
