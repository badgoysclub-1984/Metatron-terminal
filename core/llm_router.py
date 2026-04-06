#!/usr/bin/env python3
"""
METATRON QUANTUM OS — core/llm_router.py  v3.1
Z9 LLM Router — Ollama model selection, multi-turn history,
streaming, latency tracking, graceful fallback.

Routing is Z9-charge-aligned:
  Code / technical   → qwen2.5-coder:3b         (charge 6 domain)
  Reasoning / sci    → deepseek-coder-v2:lite   (charge 3 domain)
  General / default  → huihui_ai/gemma3-abliterated:4b (charge 0 domain)
"""

import json
import time
import logging
from collections import deque
from typing import Any, Dict, Generator, List, Optional

log = logging.getLogger("metatron.llm")

# ── Model registry ─────────────────────────────────────────────
MODELS = {
    "gemma_abl":  "huihui_ai/gemma3-abliterated:4b",
    "qwen_coder": "qwen2.5-coder:3b",
    "deepseek":   "deepseek-coder-v2:lite",
    "metatron":   "z9-gemma-abliterated",   # custom Modelfile variant
}

CODE_KEYWORDS = {
    "code", "function", "class", "bug", "error", "syntax",
    "python", "javascript", "html", "css", "bash", "script",
    "implement", "refactor", "debug", "compile", "claw",
    "algorithm", "variable", "loop", "import", "module", "def ",
}
REASON_KEYWORDS = {
    "reason", "explain", "science", "physics", "math",
    "theory", "proof", "derive", "analyse", "analyze",
    "why", "how does", "what is", "understand", "z9",
    "symmetry", "gauge", "quantum", "tensor", "hamiltonian",
    "anomaly", "seesaw", "yukawa", "froggatt", "nielsen",
}
SEARCH_KEYWORDS = {
    "search", "find", "google", "look up", "browse", "fetch",
    "web", "query", "ask", "tell me", "where is", "how many",
}

SYSTEM_PROMPT = (
    "You are METATRON, a ℤ₉ quantum agentic AI running on Raspberry Pi 500. "
    "You operate under ℤ₉ discrete gauge symmetry (arXiv:2604.XXXXX). "
    "Be concise, scientifically precise, and technically accurate. "
    "When discussing Z9 symmetry, reference the three charge cosets {0,3,6}, "
    "digital root 9 neutrality, retrocausal correction, and Fibonacci pulsing. "
    "Format code in markdown code blocks. Use $...$ for inline LaTeX."
)

# Maximum conversation turns retained per session
MAX_HISTORY_TURNS = 12


class Z9LLMRouter:
    """
    Routes prompts to the appropriate Ollama model.
    Maintains per-session conversation history for multi-turn chat.
    Handles streaming, retries, latency tracking, graceful fallback.
    """

    def __init__(self, timeout: int = 120, max_retries: int = 2):
        self.timeout     = timeout
        self.max_retries = max_retries
        self._latency:   List[float] = []
        self._successes: List[bool]  = []
        # session_id → deque of {"role": ..., "content": ...}
        self._histories: Dict[str, deque] = {}

        try:
            import ollama as _ol
            self._ollama   = _ol
            self._available = True
            log.info("Ollama: available")
        except ImportError:
            self._ollama   = None
            self._available = False
            log.warning("Ollama not installed — LLM in fallback mode")

    # ── Public API ─────────────────────────────────────────────

    def route(
        self,
        prompt: str,
        model: str = "auto",
        agent_context: Optional[Dict] = None,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        action_idx: int = 0,
    ) -> str:
        """Route prompt → model → full text response."""
        if not self._available:
            return self._fallback(prompt, agent_context)

        selected = self._select_model(prompt, model)
        messages = self._build_messages(
            prompt, agent_context, system_prompt, session_id
        )

        # Action-aware temperature: 0=standard, 1=precise, 2=creative
        temp = {0: 0.7, 1: 0.1, 2: 1.2}.get(action_idx, 0.7)

        for attempt in range(self.max_retries):
            t0 = time.time()
            try:
                resp = self._ollama.chat(
                    model=selected,
                    messages=messages,
                    options={"num_ctx": 4096, "temperature": temp},
                )
                text = resp["message"]["content"]
                lat  = time.time() - t0
                self._latency.append(lat)
                self._successes.append(True)
                log.debug(f"LLM [{selected}] {lat:.2f}s")

                # Persist to history
                if session_id:
                    self._push_history(session_id, "user",      prompt)
                    self._push_history(session_id, "assistant", text)

                return text
            except Exception as exc:
                log.warning(f"Ollama attempt {attempt+1}/{self.max_retries}: {exc}")
                if attempt == self.max_retries - 1:
                    self._successes.append(False)
                    return self._fallback(prompt, agent_context)
                time.sleep(0.5)

        return self._fallback(prompt, agent_context)

    def stream(
        self,
        prompt: str,
        model: str = "auto",
        agent_context: Optional[Dict] = None,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        action_idx: int = 0,
    ) -> Generator[str, None, None]:
        """Stream tokens from Ollama model. Yields text chunks."""
        if not self._available:
            yield self._fallback(prompt, None)
            return

        selected = self._select_model(prompt, model)
        messages = self._build_messages(prompt, agent_context, system_prompt, session_id)
        full_text = []

        # Action-aware temperature: 0=standard, 1=precise, 2=creative
        temp = {0: 0.7, 1: 0.1, 2: 1.2}.get(action_idx, 0.7)

        try:
            for chunk in self._ollama.chat(
                model=selected,
                messages=messages,
                stream=True,
                options={"num_ctx": 4096, "temperature": temp},
            ):
                text = chunk.get("message", {}).get("content", "")
                if text:
                    full_text.append(text)
                    yield text
        except Exception as exc:
            yield f"\n[Stream error: {exc}]"
            return

        # Persist completed response to history
        if session_id and full_text:
            self._push_history(session_id, "user",      prompt)
            self._push_history(session_id, "assistant", "".join(full_text))

    def chat_direct(
        self,
        prompt: str,
        model: str = "auto",
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Multi-turn chat: returns reply + updated history length."""
        reply = self.route(
            prompt,
            model=model,
            system_prompt=system_prompt,
            session_id=session_id,
        )
        history_len = len(self._histories.get(session_id or "", []))
        return {
            "reply":       reply,
            "model":       self._select_model(prompt, model),
            "session_id":  session_id,
            "history_len": history_len,
        }

    def clear_history(self, session_id: str):
        """Clear conversation history for a session."""
        self._histories.pop(session_id, None)

    def available_models(self) -> List[Dict]:
        """Return models currently available in Ollama."""
        if not self._available:
            return [{"name": v, "status": "not_pulled", "key": k}
                    for k, v in MODELS.items()]
        try:
            result  = self._ollama.list()
            pulled  = {m["name"] for m in result.get("models", [])}
            return [
                {"name": v, "key": k,
                 "status": "ready" if v in pulled else "not_pulled"}
                for k, v in MODELS.items()
            ]
        except Exception:
            return [{"name": v, "status": "unknown", "key": k}
                    for k, v in MODELS.items()]

    # ── Internal helpers ───────────────────────────────────────

    def _select_model(self, prompt: str, model: str) -> str:
        if model not in ("auto", ""):
            if model in MODELS:
                return MODELS[model]
            if "/" in model or ":" in model:
                return model
        pl = prompt.lower()
        if any(k in pl for k in SEARCH_KEYWORDS):
            return MODELS["metatron"]
        if any(k in pl for k in CODE_KEYWORDS):
            return MODELS["qwen_coder"]
        if any(k in pl for k in REASON_KEYWORDS):
            return MODELS["deepseek"]
        return MODELS["gemma_abl"]

    def _build_messages(
        self,
        prompt: str,
        agent_context: Optional[Dict],
        system_prompt: Optional[str],
        session_id: Optional[str],
    ) -> List[Dict]:
        sys_content = system_prompt or SYSTEM_PROMPT
        if agent_context:
            ctx = json.dumps(agent_context, indent=2, default=str)[:600]
            sys_content += f"\n\nAgent context:\n{ctx}"

        messages: List[Dict] = [{"role": "system", "content": sys_content}]

        # Inject conversation history
        if session_id and session_id in self._histories:
            messages.extend(list(self._histories[session_id]))

        messages.append({"role": "user", "content": prompt})
        return messages

    def _push_history(self, session_id: str, role: str, content: str):
        if session_id not in self._histories:
            self._histories[session_id] = deque(maxlen=MAX_HISTORY_TURNS * 2)
        self._histories[session_id].append({"role": role, "content": content})

    def _fallback(self, prompt: str, context: Optional[Dict]) -> str:
        pl = prompt.lower()
        if any(k in pl for k in ["status", "cpu", "memory", "temperature"]):
            return "[System status — use /api/status or say 'status']"
        if any(k in pl for k in ["file", "list", "folder", "directory"]):
            return "[File op dispatched to FileAgent (charge 0). Check the file panel.]"
        if any(k in pl for k in CODE_KEYWORDS):
            return (
                "[Code request — install Ollama + qwen2.5-coder:3b for AI code help]\n"
                "  curl -fsSL https://ollama.com/install.sh | sh\n"
                "  ollama pull qwen2.5-coder:3b"
            )
        return (
            "[METATRON LLM offline — Ollama not available]\n"
            "Install: curl -fsSL https://ollama.com/install.sh | sh\n"
            "Then:    ollama pull huihui_ai/gemma3-abliterated:4b"
        )

    # ── Metrics ────────────────────────────────────────────────

    @property
    def avg_latency(self) -> float:
        recent = self._latency[-50:]
        return sum(recent) / len(recent) if recent else 0.0

    @property
    def success_rate(self) -> float:
        recent = self._successes[-100:]
        return sum(recent) / len(recent) if recent else 1.0

    @property
    def is_available(self) -> bool:
        return self._available
