#!/usr/bin/env python3
"""
METATRON OS — core/fibonacci_noise.py
Fibonacci Pulsed Noise Cancellation
Based on Section 6 of arXiv:2604.XXXXX

Fibonacci-sequence pulse pattern applied to agent embeddings to
improve robustness against sensor/network noise on Pi hardware.
"""

import torch
import torch.nn as nn
import math
from typing import List

FIB_12 = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]


def fibonacci_seq(n: int) -> List[int]:
    """Return the first n Fibonacci numbers (1-indexed, starting 1,1,...)."""
    seq = [1, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]


class FibonacciNoiseCanceller(nn.Module):
    """
    Applies a learnable Fibonacci-pattern comb filter to an embedding.

    For each of the 9 Z9 modes:
        pulse_i = fib_param_i * sin(2*pi*i/9) * noise_estimate
        output  = embedding + pulse (broadcast) * 0.15
    """

    def __init__(self):
        super().__init__()
        fib9 = torch.tensor(
            [FIB_12[i % len(FIB_12)] for i in range(9)], dtype=torch.float32
        )
        self.fib_pulse = nn.Parameter(fib9)

    def forward(
        self, embedding: torch.Tensor, noise_estimate: float = 0.0
    ) -> torch.Tensor:
        device = embedding.device
        comb = torch.sin(
            2 * torch.pi * torch.arange(9, device=device, dtype=torch.float32) / 9
        )
        pulse = self.fib_pulse.to(device) * comb * noise_estimate  # shape (9,)
        # project 9-dim pulse to embedding dim via mean broadcast
        pulse_scalar = pulse.mean() * 0.15
        return embedding + pulse_scalar

    @staticmethod
    def estimate_noise(signal: torch.Tensor) -> float:
        """
        Lightweight noise estimator: normalised std of signal fluctuations.
        Used to auto-set noise_estimate for Pi sensor inputs.
        """
        if signal.numel() < 2:
            return 0.0
        return float(signal.std() / (signal.abs().mean() + 1e-8))
