#!/usr/bin/env python3
"""
METATRON OS — agents/app_agent.py
AppAgent (charge = 6)
Launches and manages local applications and processes.
"""

import os
import signal
import subprocess
from typing import Any, Dict, List, Optional

import psutil

from agents.base_agent import Z9Agent

# Map friendly names to Raspberry Pi OS / Debian executables
APP_MAP = {
    "terminal":     ["lxterminal"],
    "fileman":      ["pcmanfm"],
    "browser":      ["chromium-browser"],
    "editor":       ["mousepad"],
    "texteditor":   ["mousepad"],
    "calculator":   ["galculator"],
    "vlc":          ["vlc"],
    "thunar":       ["thunar"],
    "geany":        ["geany"],
    "nano":         ["lxterminal", "-e", "nano"],
    "python":       ["lxterminal", "-e", "python3"],
    "htop":         ["lxterminal", "-e", "htop"],
}


class AppAgent(Z9Agent):
    """Z9 agent with charge 6: process and application management."""

    def __init__(self):
        super().__init__(name="AppAgent", charge=6)
        self._managed: Dict[int, subprocess.Popen] = {}   # pid -> process

    def execute(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        action: str = "launch",
    ) -> Dict[str, Any]:
        """
        Actions:
          launch  – start an application
          kill    – kill process by PID (app_name should be the PID string)
          list    – list running managed processes
          info    – get process info by PID
        """
        try:
            if action == "kill":
                return self._kill(int(app_name))
            elif action == "list":
                return self._list_managed()
            elif action == "info":
                return self._process_info(int(app_name))
            else:
                return self._launch(app_name, args or [])
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── private helpers ────────────────────────────────────────

    def _launch(self, app_name: str, extra_args: List[str]) -> Dict[str, Any]:
        cmd = APP_MAP.get(app_name.lower())
        if cmd is None:
            # Try the raw name as a system command
            cmd = [app_name] + extra_args
        else:
            cmd = cmd + extra_args
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self._managed[proc.pid] = proc
        return {"success": True, "pid": proc.pid, "command": " ".join(cmd)}

    def _kill(self, pid: int) -> Dict[str, Any]:
        try:
            os.kill(pid, signal.SIGTERM)
            self._managed.pop(pid, None)
            return {"success": True, "killed_pid": pid}
        except ProcessLookupError:
            return {"success": False, "error": f"No process with PID {pid}"}

    def _list_managed(self) -> Dict[str, Any]:
        alive = {}
        for pid, proc in list(self._managed.items()):
            if proc.poll() is None:
                alive[pid] = proc.args
        self._managed = {p: pr for p, pr in self._managed.items() if pr.poll() is None}
        return {
            "success": True,
            "managed_processes": [
                {"pid": p, "command": str(c)} for p, c in alive.items()
            ],
        }

    def _process_info(self, pid: int) -> Dict[str, Any]:
        try:
            p = psutil.Process(pid)
            return {
                "success": True,
                "pid": pid,
                "name": p.name(),
                "status": p.status(),
                "cpu_percent": p.cpu_percent(interval=0.1),
                "memory_mb": round(p.memory_info().rss / 1024 / 1024, 2),
                "cmdline": " ".join(p.cmdline()),
            }
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"PID {pid} not found"}
