#!/usr/bin/env python3
"""
METATRON DESKTOP — core/z9_constants.py
Shared ℤ₉ framework constants (arXiv:2604.XXXXX)
"""

import torch

# ── Z₉ gauge parameters ───────────────────────────────────────
EPSILON        = 0.22          # Wolfsberg-like expansion parameter
LAMBDA_HPHI    = 0.70          # Higgs portal coupling (self-optimised)
V9_GEV         = 1500.0        # Z₉ symmetry-breaking scale (GeV)
C9             = 3.54e-7       # Z₉ coupling constant
V_EW           = 174.0         # EW VEV (GeV)

# ── Charge cosets {0, 3, 6} ───────────────────────────────────
CHARGES        = torch.tensor([0., 3., 6.])

# ── Neural architecture ───────────────────────────────────────
D_MODEL        = 128           # reduced for Raspberry Pi 500
N_PARAMS       = 6             # tunable optimizer params
DEVICE         = torch.device("cpu")

# ── Froggatt–Nielsen Yukawa texture ───────────────────────────
Y9_COARSE = torch.tensor(
    [[1.0,         EPSILON**3,  EPSILON**6],
     [EPSILON**3,  EPSILON**6,  EPSILON**9],
     [EPSILON**6,  EPSILON**9,  EPSILON**12]],
    dtype=torch.float32,
)

# ── Fibonacci sequence (noise cancellation) ───────────────────
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]

# ── Optimizer bounds ──────────────────────────────────────────
CONFIG_KEYS   = ["epsilon", "lambda_hphi", "noise_amp",
                 "retro_strength", "recall_depth", "d_model_scale"]
CONFIG_BOUNDS = {
    "epsilon":        (0.05, 0.50),
    "lambda_hphi":    (0.30, 1.20),
    "noise_amp":      (0.02, 0.50),
    "retro_strength": (0.02, 0.50),
    "recall_depth":   (1.0,  10.0),
    "d_model_scale":  (0.5,   2.0),
}

CONFIG_DEFAULTS = {
    "epsilon": 0.22, "lambda_hphi": 0.7, "noise_amp": 0.15,
    "retro_strength": 0.1, "recall_depth": 3.0, "d_model_scale": 1.0,
}
