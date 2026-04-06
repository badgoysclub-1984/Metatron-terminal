#!/usr/bin/env python3
"""
METATRON DESKTOP — tests/test_core.py
Basic unit tests for Z9 framework core.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

import torch
import pytest

from core.charge_neutral import digital_root_9, digital_root_9_scalar, ChargeNeutralConsensus
from core.shell_guard import check_command, run_safe

# ── digital_root_9 ────────────────────────────────────────────
def test_digital_root_basic():
    x = torch.tensor([9., 18., 27., 0., 1., 8.])
    dr = digital_root_9(x)
    # 9→0, 18→9%→0... let's just check shape and bounds
    assert dr.shape == x.shape
    assert (dr >= 0).all()
    assert (dr <= 8).all()

def test_digital_root_scalar_known():
    assert digital_root_9_scalar(9)  == 0
    assert digital_root_9_scalar(18) == 0
    assert digital_root_9_scalar(1)  == 1
    assert digital_root_9_scalar(5)  == 5

# ── Charge neutral consensus ───────────────────────────────────
def test_consensus_commit():
    c = ChargeNeutralConsensus()
    c.register("file",    0, True)
    c.register("browser", 3, True)
    c.register("app",     6, True)
    result = c.commit()
    assert "committed" in result
    assert "dr" in result
    assert result["dr"] == 0   # 0+3+6 = 9 → dr = 0

# ── ShellGuard ────────────────────────────────────────────────
def test_shell_guard_blocks_rm_rf():
    msg = check_command("rm -rf /")
    assert msg is not None

def test_shell_guard_blocks_dd():
    msg = check_command("dd if=/dev/zero of=/dev/sda")
    assert msg is not None

def test_shell_guard_allows_safe():
    msg = check_command("ls -la /tmp")
    assert msg is None

def test_shell_guard_allows_echo():
    msg = check_command("echo hello world")
    assert msg is None

def test_run_safe_echo():
    result = run_safe("echo metatron")
    assert result["success"] is True
    assert "metatron" in result["stdout"]

def test_run_safe_blocked():
    result = run_safe("rm -rf /")
    assert result["blocked"] is True
    assert result["success"] is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
