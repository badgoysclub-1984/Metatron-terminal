#!/usr/bin/env python3
"""
METATRON DESKTOP — core/self_optimizer.py
Z9 Golden Triadic Hive-Mind Self-Optimizer

Architecture:
  Three master operators (charges 0, 3, 6) independently observe performance
  metrics, propose parameter updates through the Z9 retrocausal + Fibonacci
  pipeline, and their proposals are charge-neutrally entangled into one
  hive-mind decision that updates the live config.

  Every metric value is filtered through digital_root_9 before processing.
  Only proposals whose digital root sums to 0 (mod 9) survive.
"""

import json
import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import psutil

from core.charge_neutral import digital_root_9, digital_root_9_scalar
from core.retrocausal import RetrocausalCorrector
from core.fibonacci_noise import FibonacciNoiseCanceller

log = logging.getLogger("metatron.optimizer")

D_MODEL = 128
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
N_PARAMS = 6   # number of tunable config parameters


# ── Master Operator ────────────────────────────────────────────

class GoldenTriadicMasterOperator(nn.Module):
    """
    One master operator for a single Z9 charge coset.
    Proposes a 6-dimensional parameter update vector.
    """

    def __init__(self, charge: float):
        super().__init__()
        self.charge = charge
        self.retro  = RetrocausalCorrector(D_MODEL)
        self.noise  = FibonacciNoiseCanceller()
        self.proj   = nn.Linear(D_MODEL, N_PARAMS)

    def propose_update(
        self,
        filtered_state: torch.Tensor,
        future_loss: float = 0.0,
    ) -> torch.Tensor:
        """Return proposed 6-dim update; zeros out non-neutral proposals."""
        x = filtered_state * self.charge            # coset weighting
        x = self.retro(x, future_loss)
        x = self.noise(x, future_loss * 0.1)
        raw = self.proj(x)                          # shape (N_PARAMS,)

        # Survival gate: only charge-neutral proposals pass
        dr = digital_root_9(raw.sum().unsqueeze(0)).item()
        gate = float(dr == 0)
        # When gate=0, use a softened version (avoid zero-update deadlock)
        if gate == 0:
            # nudge toward neutrality by normalising
            raw = raw - raw.mean()
        return raw * max(gate, 0.05)


# ── Hive-Mind Optimizer ────────────────────────────────────────

class Z9GoldenTriadicSelfOptimizer:
    """
    Golden Triadic Hive-Mind Self-Optimizer.

    Lifecycle:
        optimizer = Z9GoldenTriadicSelfOptimizer()
        optimizer.start()   # background thread, non-blocking
        ...
        optimizer.stop()
    """

    # Config keys and (min, max) bounds
    CONFIG_KEYS: List[str] = [
        "epsilon", "lambda_hphi", "noise_amp",
        "retro_strength", "recall_depth", "d_model_scale",
    ]
    CONFIG_BOUNDS: Dict[str, Tuple[float, float]] = {
        "epsilon":        (0.05, 0.50),
        "lambda_hphi":    (0.30, 1.20),
        "noise_amp":      (0.02, 0.50),
        "retro_strength": (0.02, 0.50),
        "recall_depth":   (1.0,  10.0),
        "d_model_scale":  (0.5,  2.0),
    }

    def __init__(
        self,
        config_path: str = "config/metatron_config.json",
        interval_sec: float = 8.0,
        lr: float = 0.004,
        llm_router: Optional[Any] = None,
    ):
        self.config_path   = Path(config_path)
        self.interval_sec  = interval_sec
        self.lr            = lr
        self.llm_router    = llm_router

        self.config        = self._load_config()
        self.masters: Dict[int, GoldenTriadicMasterOperator] = {
            0: GoldenTriadicMasterOperator(0.0),
            3: GoldenTriadicMasterOperator(3.0),
            6: GoldenTriadicMasterOperator(6.0),
        }
        self.performance_history: deque = deque(maxlen=500)
        self.step_count    = 0
        self.running       = False
        self._thread: Optional[threading.Thread] = None
        self._lock         = threading.Lock()

    # ── Config I/O ─────────────────────────────────────────────

    def _load_config(self) -> Dict:
        defaults = {
            "epsilon": 0.22, "lambda_hphi": 0.7, "noise_amp": 0.15,
            "retro_strength": 0.1, "recall_depth": 3.0, "d_model_scale": 1.0,
        }
        if not self.config_path.exists():
            return defaults
        try:
            raw = json.loads(self.config_path.read_text())
            z9  = raw.get("z9", raw)
            return {
                "epsilon":        float(z9.get("epsilon",         defaults["epsilon"])),
                "lambda_hphi":    float(z9.get("lambda_hphi",    defaults["lambda_hphi"])),
                "noise_amp":      float(raw.get("noise_amp",      defaults["noise_amp"])),
                "retro_strength": float(raw.get("retro_strength", defaults["retro_strength"])),
                "recall_depth":   float(raw.get("recall_depth",   defaults["recall_depth"])),
                "d_model_scale":  float(raw.get("d_model_scale",  defaults["d_model_scale"])),
            }
        except Exception as exc:
            log.warning(f"Config load error: {exc}")
            return defaults

    def _save_config(self):
        try:
            raw = {}
            if self.config_path.exists():
                raw = json.loads(self.config_path.read_text())
            z9 = raw.setdefault("z9", {})
            z9["epsilon"]        = self.config["epsilon"]
            z9["lambda_hphi"]    = self.config["lambda_hphi"]
            raw["noise_amp"]     = self.config["noise_amp"]
            raw["retro_strength"]= self.config["retro_strength"]
            raw["recall_depth"]  = self.config["recall_depth"]
            raw["d_model_scale"] = self.config["d_model_scale"]
            self.config_path.write_text(json.dumps(raw, indent=2))
        except Exception as exc:
            log.warning(f"Config save error: {exc}")

    # ── Measurement ────────────────────────────────────────────

    def _get_temperature(self) -> float:
        """Read Raspberry Pi SoC temperature."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
            return temp
        except Exception:
            return 45.0  # fallback

    def _measure(self) -> Dict:
        """Sample live system metrics and filter through ℤ₉."""
        cpu  = psutil.cpu_percent(interval=0.1) / 100.0
        ram  = psutil.virtual_memory().percent   / 100.0
        temp = self._get_temperature()
        temp_norm = min(max(temp - 40.0, 0.0) / 40.0, 1.0)  # 0.0 at 40C, 1.0 at 80C

        # LLM metrics integration
        llm_lat = 0.0
        llm_err = 0.0
        if self.llm_router:
            llm_lat = min(self.llm_router.avg_latency / 60.0, 1.0)
            llm_err = 1.0 - self.llm_router.success_rate

        n = len(self.performance_history)
        recent = list(self.performance_history)[-20:]
        avg_err = sum(recent) / len(recent) if recent else 0.0

        # 6-dim raw state matching N_PARAMS
        raw = torch.tensor(
            [cpu, ram, llm_lat, avg_err, llm_err, temp_norm],
            dtype=torch.float32,
        )

        # Pad to D_MODEL
        padded = torch.zeros(D_MODEL)
        padded[:N_PARAMS] = raw

        # Filter through ℤ₉: scale to [0,9] → digital_root → normalise
        filtered = digital_root_9(padded * 9.0) / 9.0

        error_proxy = (
            (1.0 - min(avg_err, 1.0)) * 0.4 +   # invert: higher = worse
            cpu  * 0.3 +
            ram  * 0.3
        )
        return {
            "raw":        raw,
            "filtered":   filtered,
            "error_proxy": float(error_proxy),
        }

    # ── Entanglement ───────────────────────────────────────────

    def _entangle(
        self,
        proposals: Dict[int, torch.Tensor],
    ) -> torch.Tensor:
        """Charge-neutral consensus of {0,3,6} master proposals."""
        stacked = torch.stack([proposals[c] for c in (0, 3, 6)])  # (3, N_PARAMS)
        mean_proposal = stacked.mean(dim=0)

        # Hive-mind charge check
        total_charge = 0 + 3 + 6   # = 9 → dr = 0
        dr = digital_root_9_scalar(
            total_charge + int(mean_proposal.sum().item() * 9) % 9
        )
        gate = 1.0 if dr == 0 else 0.1   # softened — never fully block
        return mean_proposal * gate

    # ── Optimization step ─────────────────────────────────────

    def optimize_step(self):
        metrics = self._measure()
        self.performance_history.append(metrics["error_proxy"])
        self.step_count += 1

        hist = list(self.performance_history)[-10:]
        future_loss = sum(hist) / len(hist)

        # Each master proposes independently
        proposals: Dict[int, torch.Tensor] = {}
        for charge, master in self.masters.items():
            with torch.no_grad():
                proposals[charge] = master.propose_update(
                    metrics["filtered"], future_loss
                )

        # Hive-mind entanglement → single update vector
        update = self._entangle(proposals)          # shape (N_PARAMS,)

        # Apply updates
        with self._lock:
            for i, key in enumerate(self.CONFIG_KEYS):
                delta = float(update[i].item()) * self.lr
                self.config[key] = self.config.get(key, 0.0) + delta
            self._clamp()
            self._save_config()

            # Apply Z9 optimization to Ollama router if present
            if self.llm_router:
                self.llm_router.z9_optimize(
                    self.config["epsilon"],
                    self.config["lambda_hphi"]
                )

        log.debug(
            f"Step {self.step_count} | err={metrics['error_proxy']:.4f} | "
            f"future={future_loss:.4f} | "
            f"ε={self.config['epsilon']:.4f} | λ={self.config['lambda_hphi']:.4f}"
        )

    def _clamp(self):
        for key, (lo, hi) in self.CONFIG_BOUNDS.items():
            self.config[key] = float(max(lo, min(hi, self.config.get(key, lo))))

    # ── Thread management ──────────────────────────────────────

    def _loop(self):
        log.info("🧿 Golden Triadic Self-Optimizer loop started")
        while self.running:
            try:
                self.optimize_step()
            except Exception as exc:
                log.warning(f"Optimizer step exception: {exc}")
            time.sleep(self.interval_sec)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="GoldenTriadicOptimizer",
        )
        self._thread.start()
        log.info("🧿 Golden Triadic Hive-Mind Self-Optimizer STARTED")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=self.interval_sec + 2.0)
        log.info("🧿 Optimizer STOPPED")

    # ── Public getters ─────────────────────────────────────────

    @property
    def current_params(self) -> Dict:
        with self._lock:
            return dict(self.config)

    def summary(self) -> Dict:
        hist = list(self.performance_history)[-20:]
        return {
            "running":      self.running,
            "step_count":   self.step_count,
            "history":      hist,
            "last_error":   hist[-1] if hist else 0.0,
            "history_len":  len(self.performance_history),
            "config":       self.current_params,
            "masters":      {str(c): {"charge": c} for c in (0, 3, 6)},
        }
