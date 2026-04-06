#!/usr/bin/env python3
"""
METATRON DESKTOP — core/shell_guard.py
Safe shell command execution with allowlist/blocklist enforcement.

The Z9 SystemAgent runs arbitrary shell commands, which is intentional
(this is a local-only OS for your own Pi).  This module adds a soft
safety layer:
  - Blocks commands that could destroy the OS itself.
  - Warns on high-privilege patterns (sudo rm -rf /, dd, mkfs …).
  - Enforces a timeout (default 30 s).
  - Strips ANSI escape codes from output.
  - Returns a structured dict compatible with SystemAgent.execute().
"""

import re
import shlex
import subprocess
import logging
from typing import List, Optional

log = logging.getLogger("metatron.shell")

# ── Commands always blocked ────────────────────────────────────
HARD_BLOCK: List[str] = [
    r"rm\s+-rf\s+/",          # rm -rf /
    r"dd\s+if=.*of=/dev/",    # dd to a block device
    r"mkfs",                  # format a partition
    r":\(\){ :\|:& };:",     # fork bomb
    r"chmod\s+-R\s+777\s+/",  # 777 on root
    r">\s*/etc/passwd",       # overwrite passwd
    r"curl.*\|.*sh",          # curl-pipe-bash
    r"wget.*\|.*sh",
]

# ── Commands that trigger a warning but are allowed ───────────
WARN_PATTERNS: List[str] = [
    r"\bsudo\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"apt(-get)?\s+(remove|purge|autoremove)",
]

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def check_command(cmd: str) -> Optional[str]:
    """
    Returns an error message if the command is hard-blocked,
    or None if it is allowed.
    """
    for pat in HARD_BLOCK:
        if re.search(pat, cmd, re.IGNORECASE):
            return f"Blocked: matches safety pattern /{pat}/"
    return None


def run_safe(
    cmd: str,
    timeout: int = 30,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> dict:
    """
    Execute *cmd* in a shell with safety checks.

    Returns a dict:
        { success, stdout, stderr, returncode, blocked, warning }
    """
    # Hard block
    block_msg = check_command(cmd)
    if block_msg:
        log.warning(f"ShellGuard BLOCKED: {cmd!r} → {block_msg}")
        return {
            "success":    False,
            "stdout":     "",
            "stderr":     "",
            "returncode": -1,
            "blocked":    True,
            "warning":    block_msg,
            "command":    cmd,
        }

    # Soft warn
    warning = None
    for pat in WARN_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            warning = f"Warning: command matches elevated-privilege pattern /{pat}/"
            log.warning(f"ShellGuard WARN: {cmd!r}")
            break

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
        return {
            "success":    result.returncode == 0,
            "stdout":     strip_ansi(result.stdout)[:8192],
            "stderr":     strip_ansi(result.stderr)[:2048],
            "returncode": result.returncode,
            "blocked":    False,
            "warning":    warning,
            "command":    cmd,
        }
    except subprocess.TimeoutExpired:
        return {
            "success":    False,
            "stdout":     "",
            "stderr":     f"Timeout after {timeout}s",
            "returncode": -1,
            "blocked":    False,
            "warning":    warning,
            "command":    cmd,
        }
    except Exception as exc:
        return {
            "success":    False,
            "stdout":     "",
            "stderr":     str(exc),
            "returncode": -1,
            "blocked":    False,
            "warning":    warning,
            "command":    cmd,
        }
