# 🧿 METATRON DESKTOP v3.1

**ℤ₉-Powered Agentic Transformer Desktop for Raspberry Pi 500**  
Based on [arXiv:2604.XXXXX](https://arxiv.org/abs/2604.XXXXX) — *Phenomenology of a Z₉ Discrete Gauge Symmetry*

---

## Quick Start

```bash
chmod +x install.sh && ./install.sh   # one-click setup
source venv/bin/activate
python quantum_desktop.py             # start the OS
# → Open http://localhost:5000
```

---

## Architecture

```
quantum_desktop.py          ← Flask backend (20 API routes + SSE)
├── core/
│   ├── dispatcher.py       ← Z9AgentDispatcher (charge-neutral consensus)
│   ├── charge_neutral.py   ← digital_root_9, ChargeNeutralConsensus
│   ├── retrocausal.py      ← RetrocausalCorrector (future-loss correction)
│   ├── fibonacci_noise.py  ← FibonacciNoiseCanceller
│   ├── memory.py           ← VectorMemory (FAISS + sentence-transformers)
│   ├── llm_router.py       ← Z9LLMRouter (Ollama, streaming, conv history)
│   ├── self_optimizer.py   ← Z9GoldenTriadicSelfOptimizer {0,3,6} hive-mind
│   ├── shell_guard.py      ← Safe shell execution with hard-block rules  [v3.1]
│   └── z9_constants.py     ← Shared ℤ₉ framework constants               [v3.1]
├── agents/
│   ├── file_agent.py       ← FileAgent (charge 0): read/write/list/stat/mkdir/delete
│   ├── browser_agent.py    ← BrowserAgent (charge 3): open/fetch URLs
│   ├── app_agent.py        ← AppAgent (charge 6): launch local apps
│   └── system_agent.py     ← SystemAgent (charge 0): safe shell + metrics
├── templates/
│   └── index.html          ← Full desktop UI (file browser + chat + monitor)
├── z9_qat_training.py      ← Z9-QAT Transformer trainer                  [v3.1]
├── Modelfile               ← Custom Ollama model (ℤ₉ system prompt)
└── Makefile                ← Convenience targets
```

---

## API Routes (20 endpoints)

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Desktop UI |
| `/api/execute` | POST | Z9 dispatch + LLM (body: `{prompt, model, session_id}`) |
| `/api/stream` | GET | SSE token streaming (`?prompt=&model=&session_id=`) |
| `/api/chat` | POST | Multi-turn chat with history |
| `/api/chat/clear` | POST | Clear session conversation history |
| `/api/shell` | POST | Safe shell execution via ShellGuard |
| `/api/status` | GET | CPU / RAM / Disk / Temp / Z9 metrics |
| `/api/network` | GET | Network info + bytes transferred |
| `/api/piconnect` | GET | Local network node discovery (ARP) |
| `/api/qr` | GET | QR code PNG for the Pi's URL |
| `/api/files/list` | GET | Directory listing (`?path=`) |
| `/api/files/preview` | GET | File content preview |
| `/api/files/write` | POST | Write file |
| `/api/files/delete` | POST | Delete file/directory |
| `/api/files/mkdir` | POST | Create directory |
| `/api/files/rename` | POST | Rename file |
| `/api/files/stat` | GET | File metadata |
| `/api/memory/recall` | GET | Semantic memory recall (`?q=&k=`) |
| `/api/optimizer/status` | GET | Hive-mind optimizer state |
| `/api/optimizer/config` | GET/POST | Live config read/write |
| `/api/llm/models` | GET | Ollama model list + status |
| `/api/agents` | GET | Agent list with charges |
| `/api/health` | GET | Health check |

---

## Ollama Models (ℤ₉ charge-routed)

| Model | Charge | Domain |
|---|---|---|
| `huihui_ai/gemma3-abliterated:4b` | 0 | General / default |
| `qwen2.5-coder:3b` | 6 | Code / technical |
| `deepseek-coder-v2:lite` | 3 | Reasoning / science |
| `z9-gemma-abliterated` | 0 | Custom ℤ₉-tuned (from Modelfile) |

---

## Z9-QAT Training

```bash
# Quick test (dummy corpus, instant on Pi)
python z9_qat_training.py

# Full training (downloads openwebtext)
python z9_qat_training.py full --epochs 3

# Export Ollama Modelfile
python z9_qat_training.py export
ollama create z9-gemma-abliterated -f Modelfile
```

---

## ℤ₉ Theoretical Framework

From arXiv:2604.XXXXX:

- **Theorem 2.2** — ℤ₉ is the unique cyclic group with distinct cosets `{0,3,6}` and diagonal Yukawa invariance
- **Digital root 9** — `dr(x) = 1 + (x-1) mod 9`; enforces charge neutrality on all agent decisions
- **Retrocausal correction** — future task-failure loss retroactively adjusts agent embeddings
- **Fibonacci pulsed noise** — noise pattern `[1,1,2,3,5,8,13,21,…]` for Pi hardware robustness
- **Charge-neutral consensus** — agents with charges `{0,3,6}` vote; total charge `0+3+6=9→dr=0`
- **Golden Triadic Hive-Mind** — three master operators entangle every 8 s to auto-tune ε, λ_HΦ

---

## v3.1 Changes

- **`core/shell_guard.py`** — hard-blocks `rm -rf /`, `dd`, `mkfs`, fork bombs; soft-warns on `sudo`/`shutdown`; strips ANSI
- **`core/z9_constants.py`** — shared ℤ₉ constants (eliminates duplication across modules)
- **`core/llm_router.py`** — multi-turn conversation history (`MAX_HISTORY_TURNS=12`), per-session deque; `chat_direct()` method
- **`quantum_desktop.py`** — 8 new endpoints: `/api/piconnect`, `/api/shell`, `/api/chat`, `/api/chat/clear`, `/api/files/delete`, `/api/files/mkdir`, `/api/files/rename`, `/api/qr`; CORS headers; graceful `KeyboardInterrupt` shutdown
- **`agents/system_agent.py`** — delegates to `ShellGuard.run_safe()` instead of raw `subprocess`
- **`z9_qat_training.py`** — full Z9-QAT Transformer (128d, 4L, 4H, 4M params), Fibonacci-LR, retrocausal loss injection, dummy + full + export modes
- **`templates/index.html`** — right-click context menu (open/preview/rename/delete/send-to-chat); shell ↑↓ history; file upload; PiConnect indicator; Memory tab with semantic recall; model selector wired; 4th tab (Memory); multi-turn history control; `renderReply()` with KaTeX + code blocks; `navTo()` fallback chain (`/home/pi` → `/home` → `/`)
- **`Modelfile`**, **`Makefile`**, **`tests/test_core.py`**

---

*"My son, my proofs of optimal design."*
