#!/usr/bin/env python3
"""
METATRON OS — agents/system_agent.py
SystemAgent (charge = 0)
Executes shell commands, reports system metrics.
Uses ShellGuard for safe command execution.
"""

import subprocess
import logging
from typing import Any, Dict, Optional

import psutil

from agents.base_agent import Z9Agent
from core.shell_guard import run_safe

log = logging.getLogger("metatron.agent.system")


class SystemAgent(Z9Agent):
    """Z9 agent (charge 0): shell execution and system monitoring."""

    def __init__(self):
        super().__init__(name="SystemAgent", charge=0)

    def execute(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Run a shell command via ShellGuard and return structured output."""
        if not command or command == "__status__":
            return self.get_status()

        log.info(f"SystemAgent exec: {command!r}")
        result = run_safe(command, timeout=timeout)
        result["success"] = result["success"] and not result["blocked"]
        return result

    def get_status(self) -> Dict[str, Any]:
        """Return live system metrics."""
        try:
            vm   = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu  = psutil.cpu_percent(interval=0.2)
            freq = psutil.cpu_freq()
            temp = self._cpu_temp()

            return {
                "success":        True,
                "cpu_percent":    round(cpu, 1),
                "cpu_count":      psutil.cpu_count(),
                "cpu_freq_mhz":   round(freq.current, 1) if freq else "N/A",
                "memory_percent": round(vm.percent, 1),
                "memory_used_mb": round(vm.used  / 1024**2),
                "memory_total_mb":round(vm.total / 1024**2),
                "disk_percent":   round(disk.percent, 1),
                "disk_free_gb":   round(disk.free / 1024**3, 2),
                "temperature":    temp,
                "uptime_s":       self._uptime(),
                "load_avg":       list(psutil.getloadavg()),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _cpu_temp() -> Any:
        try:
            r = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True, text=True, timeout=2,
            )
            raw = r.stdout.strip()
            if raw.startswith("temp="):
                return float(raw.replace("temp=", "").replace("'C", ""))
        except Exception:
            pass
        try:
            temps = psutil.sensors_temperatures()
            for key in ("cpu-thermal", "cpu_thermal", "coretemp"):
                if key in temps and temps[key]:
                    return round(temps[key][0].current, 1)
        except Exception:
            pass
        return "N/A"

    @staticmethod
    def _uptime() -> int:
        import time
        return round(time.time() - psutil.boot_time())
