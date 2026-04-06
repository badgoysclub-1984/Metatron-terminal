#!/usr/bin/env python3
"""
METATRON OS — agents/base_agent.py
Abstract Z9Agent base class with charge, digital-root enforcement,
retrocausal correction, and Fibonacci noise cancellation.
"""

import torch
import torch.nn as nn
from typing import List, Tuple

from core.charge_neutral import digital_root_9, VALID_CHARGES
from core.retrocausal import RetrocausalCorrector
from core.fibonacci_noise import FibonacciNoiseCanceller

D_MODEL = 128
EPSILON = 0.22
LAMBDA_HPHI_BASE = 0.7


class Z9Agent(nn.Module):
    """
    Abstract agent carrying a Z9 gauge charge in {0, 3, 6}.

    Each agent has:
      - A learnable embedding (the agent's "state")
      - A RetrocausalCorrector  (future-loss feedback)
      - A FibonacciNoiseCanceller (Pi hardware robustness)
      - An action head  (outputs 3-way action logits)
      - Digital-root enforcement on logits sum

    Sub-classes implement execute(**kwargs) for their specific domain.
    """

    def __init__(self, name: str, charge: int, d_model: int = D_MODEL):
        super().__init__()
        if charge not in VALID_CHARGES:
            raise ValueError(f"Charge must be in {VALID_CHARGES}, got {charge}")
        self.name = name
        self.charge = charge
        self.d_model = d_model
        self.epsilon = EPSILON
        self.lambda_hphi = LAMBDA_HPHI_BASE

        # Learnable parameters
        self.embedding = nn.Parameter(torch.randn(d_model) * 0.1)
        self.retro = RetrocausalCorrector(d_model)
        self.noise = FibonacciNoiseCanceller()
        self.action_head = nn.Linear(d_model, 3)   # 3 action modes

        # Experience buffer
        self.memory: List[Tuple[torch.Tensor, int, float]] = []  # (obs, action, reward)

    # ──────────────────────────────────────────────────────────
    def forward(
        self,
        observation: torch.Tensor,
        future_loss: float = 0.0,
        noise_estimate: float = 0.0,
    ) -> torch.Tensor:
        """
        Z9-charged forward pass.

        1. Scale observation by charge (coset weighting)
        2. Add learnable embedding
        3. Apply retrocausal correction
        4. Apply Fibonacci noise cancellation
        5. Project through action_head
        6. Enforce digital-root 9 on logit sum
        """
        # Step 1-2: charge-scaled state
        x = observation * float(self.charge) + self.embedding

        # Step 3-4: corrections
        x = self.retro(x, future_loss)
        x = self.noise(x, noise_estimate)

        # Step 5: action logits
        logits = self.action_head(x)          # shape (3,)

        # Step 6: digital-root enforcement
        dr = digital_root_9(torch.sum(logits).unsqueeze(0)).item()
        if dr != 0:
            # Shift logits so their sum becomes charge-neutral
            logits = logits - logits.mean() * (dr / 9.0)

        return logits

    def act(
        self,
        observation: torch.Tensor,
        future_loss: float = 0.0,
    ) -> int:
        """Return greedy action index {0,1,2} without gradient."""
        with torch.no_grad():
            logits = self.forward(observation, future_loss)
            return int(logits.argmax().item())

    def record_outcome(self, obs: torch.Tensor, action: int, reward: float):
        """Store (obs, action, reward) for offline learning."""
        self.memory.append((obs.clone(), action, reward))
        if len(self.memory) > 500:
            self.memory.pop(0)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} charge={self.charge} d_model={self.d_model}>"
