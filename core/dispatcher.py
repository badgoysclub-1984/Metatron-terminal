#!/usr/bin/env python3
"""
METATRON OS — core/dispatcher.py
Z9 Agent Dispatcher with charge-neutral consensus
"""

import os
import re
import torch
from collections import deque
from typing import Any, Dict, Tuple

from core.charge_neutral import ChargeNeutralConsensus, digital_root_9_scalar
from agents.file_agent import FileAgent
from agents.browser_agent import BrowserAgent
from agents.app_agent import AppAgent
from agents.system_agent import SystemAgent

D_MODEL = 128


class Z9AgentDispatcher:
    """
    Parses natural-language prompts, routes to the correct Z9 agent,
    enforces charge-neutral consensus, and applies retrocausal correction
    on failure.
    """

    def __init__(self):
        self.agents = {
            "file":    FileAgent(),
            "browser": BrowserAgent(),
            "app":     AppAgent(),
            "system":  SystemAgent(),
        }
        self.consensus = ChargeNeutralConsensus()
        self.consensus_history = deque(maxlen=20)
        self.epsilon = 0.22          # Z9 expansion parameter
        self.lambda_hphi = 0.7       # portal coupling (self-optimised)
        self.task_success_rate = 1.0

    # ──────────────────────────────────────────────────────────
    # INTENT PARSER
    # ──────────────────────────────────────────────────────────
    def parse_intent(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        pl = prompt.lower()

        # FILE operations
        if any(k in pl for k in ["file", "folder", "directory", "read", "write",
                                   "delete", "list", "ls ", "cat ", "mkdir"]):
            path = self._extract_path(prompt) or os.getcwd()
            if "write" in pl or "create" in pl or "save" in pl:
                content = re.split(r"write|create|save", prompt, flags=re.I)[-1].strip()
                return "file", {"path": path, "operation": "write", "content": content}
            if "delete" in pl or "remove" in pl or "rm " in pl:
                return "file", {"path": path, "operation": "delete"}
            if "mkdir" in pl or "make dir" in pl:
                return "file", {"path": path, "operation": "mkdir"}
            return "file", {"path": path, "operation": "read"}

        # BROWSER operations
        if any(k in pl for k in ["browser", "web", "url", "http", "open", "fetch",
                                   "navigate", "search online", "google"]):
            url = self._extract_url(prompt)
            if not url:
                # Build Google search URL from prompt
                query = re.sub(r"(search|google|browse|look up|fetch)", "", pl).strip()
                url = "https://www.google.com/search?q=" + "+".join(query.split())
            action = "fetch" if any(k in pl for k in ["fetch", "get", "scrape"]) else "open"
            return "browser", {"url": url, "action": action}

        # APP operations
        if any(k in pl for k in ["launch", "start", "app", "open app",
                                   "run app", "execute app"]):
            app_name = self._extract_app_name(prompt)
            args = self._extract_args(prompt)
            return "app", {"app_name": app_name, "args": args}

        # SYSTEM / SHELL operations
        if any(k in pl for k in ["status", "cpu", "memory", "temperature",
                                   "disk", "uptime", "processes"]):
            return "system", {"command": "__status__"}

        if any(k in pl for k in ["shell", "command", "run", "execute", "bash",
                                   "terminal", "sudo", "apt", "pip"]):
            cmd = re.split(r"shell|command|run|execute|bash", prompt, flags=re.I)[-1].strip()
            return "system", {"command": cmd or prompt}

        # Default: treat whole prompt as a shell command
        return "system", {"command": prompt}

    # ──────────────────────────────────────────────────────────
    # DISPATCH
    # ──────────────────────────────────────────────────────────
    def dispatch(self, prompt: str) -> Dict[str, Any]:
        agent_name, params = self.parse_intent(prompt)
        agent = self.agents[agent_name]

        # Observation vector: deterministic hash of prompt
        obs = torch.tensor(
            [abs(hash(prompt)) % 1000 / 1000.0] * D_MODEL, dtype=torch.float32
        )
        action_idx = agent.act(obs)

        # Execute task
        result = self._execute(agent_name, agent, params)
        success = result.get("success", False)

        # Charge-neutral consensus
        self.consensus.register(agent_name, agent.charge, success)
        consensus_record = self.consensus.commit()
        self.consensus_history.append(consensus_record)

        # Retrocausal correction on failure
        if not success:
            future_loss = 1.0
            obs2 = obs + future_loss
            action_idx = agent.act(obs2)
            result2 = self._execute(agent_name, agent, params)
            if result2.get("success", False):
                result = result2
                self.consensus.register(agent_name, agent.charge, True)
                consensus_record = self.consensus.commit()

        self._update_lambda(success)

        return {
            "prompt": prompt,
            "agent": agent_name,
            "charge": agent.charge,
            "action_index": action_idx,
            "result": result,
            "charge_neutral": consensus_record.get("committed", False),
            "dr": consensus_record.get("dr", -1),
            "epsilon": round(self.epsilon, 4),
            "lambda_hphi": round(self.lambda_hphi, 4),
        }

    # ──────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ──────────────────────────────────────────────────────────
    def _execute(self, agent_name: str, agent, params: Dict) -> Dict:
        try:
            if agent_name == "file":
                return agent.execute(
                    params["path"],
                    params.get("operation", "read"),
                    params.get("content"),
                )
            if agent_name == "browser":
                return agent.execute(params["url"], params.get("action", "open"))
            if agent_name == "app":
                return agent.execute(params["app_name"], params.get("args"))
            if agent_name == "system":
                if params.get("command") == "__status__":
                    return agent.get_status()
                return agent.execute(params["command"])
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        return {"success": False, "error": "Unknown agent"}

    def _extract_path(self, prompt: str) -> str:
        for token in prompt.split():
            if token.startswith("/") or token.startswith("~") or \
               (len(token) > 1 and token[1] == ":"):
                return token
        return ""

    def _extract_url(self, prompt: str) -> str:
        for token in prompt.split():
            if token.startswith("http://") or token.startswith("https://"):
                return token
        return ""

    def _extract_app_name(self, prompt: str) -> str:
        keywords = ["launch", "start", "open", "run", "app", "application"]
        words = prompt.split()
        for i, w in enumerate(words):
            if w.lower() in keywords and i + 1 < len(words):
                return words[i + 1]
        return words[-1] if words else "bash"

    def _extract_args(self, prompt: str) -> list:
        # Anything after "--" is treated as extra args
        if "--" in prompt:
            return prompt.split("--", 1)[1].strip().split()
        return []

    def _update_lambda(self, success: bool):
        """Live self-optimisation: adapt lambda_hphi from task success rate."""
        alpha = 0.05
        self.task_success_rate = (
            (1 - alpha) * self.task_success_rate + alpha * float(success)
        )
        # Portal coupling tracks success: higher success -> lower coupling needed
        self.lambda_hphi = max(0.1, min(1.0, 1.0 - self.task_success_rate * 0.3))
