#!/usr/bin/env python3
"""
METATRON DESKTOP v3.1 — quantum_desktop.py
Master Flask Backend

ℤ₉ Agentic Transformer Desktop for Raspberry Pi 500
Based on arXiv:2604.XXXXX (Phenomenology of a Z9 Discrete Gauge Symmetry)
Author: Optimal Design Systems

Architecture:
  Flask REST + SSE  ← web desktop UI
  Z9AgentDispatcher ← routes prompts to FileAgent / BrowserAgent / AppAgent / SystemAgent
  Z9LLMRouter       ← Ollama: Gemma4-abliterated · Qwen2.5-Coder · DeepSeek
  GoldenTriadic     ← background hive-mind self-optimizer {0,3,6}
  VectorMemory      ← FAISS persistent semantic recall
  ShellGuard        ← safe command execution
  ConvHistory       ← per-session multi-turn LLM context
"""

import json
import logging
import os
import socket
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import torch
import psutil
from flask import (
    Flask, jsonify, render_template, request,
    Response, stream_with_context,
)

# ── Z9 Core imports ────────────────────────────────────────────
from core.dispatcher   import Z9AgentDispatcher
from core.memory       import VectorMemory

# Optional subsystems — degrade gracefully
try:
    from core.self_optimizer import Z9GoldenTriadicSelfOptimizer
    _HAS_OPT = True
except ImportError:
    _HAS_OPT = False

try:
    from core.llm_router import Z9LLMRouter
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

try:
    import qrcode, io
    _HAS_QR = True
except ImportError:
    _HAS_QR = False


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

CONFIG_PATH = Path("config/metatron_config.json")

def _load_config() -> Dict:
    defaults = {
        "version":  "3.1",
        "name":     "METATRON DESKTOP",
        "z9":       {"epsilon": 0.22, "lambda_hphi": 0.7, "v9_gev": 1500.0},
        "web_ui":   {"host": "0.0.0.0", "port": 5000},
        "pi":       {"d_model": 128, "use_cpu": True},
        "memory":   {"persist_path": "logs/memory.json"},
        "shell":    {"timeout": 30},
    }
    if CONFIG_PATH.exists():
        try:
            raw = json.loads(CONFIG_PATH.read_text())
            defaults.update(raw)
        except Exception:
            pass
    return defaults

CONFIG = _load_config()


# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/metatron.log", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("metatron")


# ═══════════════════════════════════════════════════════════════
# APP FACTORY
# ═══════════════════════════════════════════════════════════════

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["JSON_SORT_KEYS"] = False

    # ── Shared Z9 systems ──────────────────────────────────────
    _mem_path = Path(CONFIG.get("memory", {}).get("persist_path", "logs/memory.json"))
    _mem_path.parent.mkdir(exist_ok=True)

    _dispatcher = Z9AgentDispatcher()
    _memory     = VectorMemory(persist_path=_mem_path)
    _llm        = Z9LLMRouter()                       if _HAS_LLM else None
    _optimizer  = Z9GoldenTriadicSelfOptimizer(llm_router=_llm) if _HAS_OPT else None

    if _optimizer:
        _optimizer.start()

    app.dispatcher = _dispatcher
    app.memory     = _memory
    app.llm        = _llm
    app.optimizer  = _optimizer

    # ── CORS (allow Pi-local access from any browser) ─────────
    @app.after_request
    def _cors(resp):
        resp.headers["Access-Control-Allow-Origin"]  = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return resp

    # ─────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────

    @app.route("/sw.js")
    def service_worker():
        from flask import send_from_directory
        response = send_from_directory("static", "sw.js", mimetype="application/javascript")
        response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.route("/")
    def index():
        return render_template("index.html")

    # ─────────────────────────────────────────────────────────
    # CORE DISPATCH
    # ─────────────────────────────────────────────────────────

    @app.route("/api/execute", methods=["POST", "OPTIONS"])
    def execute():
        if request.method == "OPTIONS":
            return jsonify({}), 200
        data    = request.get_json(force=True, silent=True) or {}
        prompt  = (data.get("prompt") or "").strip()
        model   = data.get("model", "auto")
        session = data.get("session_id", "default")

        if not prompt:
            return jsonify({"error": "Empty prompt"}), 400

        # 1. Z9 Agent dispatch
        try:
            agent_result = _dispatcher.dispatch(prompt)
        except Exception as exc:
            import traceback
            log.error(f"Dispatch error: {exc}\n{traceback.format_exc()}")
            agent_result = {"error": str(exc), "agent": "unknown", "charge": 0}

        # 2. LLM response
        llm_reply = ""
        if _llm:
            try:
                llm_reply = _llm.route(
                    prompt,
                    model=model,
                    agent_context=_safe_serialize(agent_result.get("result", {})),
                    session_id=session,
                    action_idx=agent_result.get("action_index", 0),
                )
            except Exception as exc:
                log.warning(f"LLM error: {exc}")
                llm_reply = f"[LLM error: {exc}]"

        # 3. Persist to memory
        try:
            _memory.add(prompt, {
                "agent":   agent_result.get("agent", "unknown"),
                "success": bool(agent_result.get("result", {}).get("success", False)),
                "ts":      time.time(),
            })
        except Exception:
            pass

        # 4. Optimizer snapshot
        opt_snap = _optimizer_snap(_optimizer)

        return jsonify({
            "agent_result": _safe_serialize(agent_result),
            "llm_reply":    llm_reply,
            "optimizer":    opt_snap,
            "session_id":   session,
        })

    # ─────────────────────────────────────────────────────────
    # SSE STREAMING
    # ─────────────────────────────────────────────────────────

    @app.route("/api/stream")
    def stream():
        prompt  = (request.args.get("prompt") or "").strip()
        model   = request.args.get("model", "auto")
        session = request.args.get("session_id", "default")

        # 1. Dispatch first to get agent context and action_idx
        try:
            agent_result = _dispatcher.dispatch(prompt)
            action_idx   = agent_result.get("action_index", 0)
            context      = _safe_serialize(agent_result.get("result", {}))
        except Exception:
            action_idx   = 0
            context      = None

        def _gen() -> Generator[str, None, None]:
            if not _llm:
                yield _sse({"text": "[Ollama not available]", "done": True})
                return
            try:
                # Include action_idx and agent_context in stream
                for chunk in _llm.stream(prompt, model=model, session_id=session,
                                         agent_context=context, action_idx=action_idx):
                    yield _sse({"text": chunk, "done": False})
                yield _sse({"text": "", "done": True})
            except Exception as exc:
                yield _sse({"error": str(exc), "done": True})

        return Response(
            stream_with_context(_gen()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ─────────────────────────────────────────────────────────
    # DEDICATED CHAT (multi-turn, history-aware)
    # ─────────────────────────────────────────────────────────

    @app.route("/api/chat", methods=["POST", "OPTIONS"])
    def chat():
        if request.method == "OPTIONS":
            return jsonify({}), 200
        data    = request.get_json(force=True, silent=True) or {}
        prompt  = (data.get("prompt") or "").strip()
        model   = data.get("model", "auto")
        session = data.get("session_id", "default")
        sys_p   = data.get("system")

        if not prompt:
            return jsonify({"error": "Empty prompt"}), 400
        if not _llm:
            return jsonify({"reply": "[Ollama not available]", "model": "none"})

        result = _llm.chat_direct(prompt, model=model,
                                   session_id=session, system_prompt=sys_p)
        return jsonify(result)

    @app.route("/api/chat/clear", methods=["POST"])
    def chat_clear():
        data    = request.get_json(force=True, silent=True) or {}
        session = data.get("session_id", "default")
        if _llm:
            _llm.clear_history(session)
        return jsonify({"cleared": True, "session_id": session})

    # ─────────────────────────────────────────────────────────
    # SYSTEM STATUS
    # ─────────────────────────────────────────────────────────

    @app.route("/api/status")
    def status():
        try:
            vm   = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu  = psutil.cpu_percent(interval=0.02)
            freq = psutil.cpu_freq()

            z9_snap = {
                "epsilon":           round(getattr(_dispatcher, "epsilon", 0.22), 6),
                "lambda_hphi":       round(getattr(_dispatcher, "lambda_hphi", 0.7), 6),
                "task_success_rate": round(getattr(_dispatcher, "task_success_rate", 1.0), 4),
                "consensus_count":   len(getattr(_dispatcher, "consensus_history", [])),
            }

            llm_snap = {}
            if _llm:
                llm_snap = {
                    "available":    _llm.is_available,
                    "avg_latency":  round(_llm.avg_latency, 3),
                    "success_rate": round(_llm.success_rate, 4),
                }

            return jsonify({
                "cpu_percent":     round(cpu, 1),
                "cpu_count":       psutil.cpu_count(),
                "cpu_freq_mhz":    round(freq.current, 1) if freq else "N/A",
                "memory_percent":  round(vm.percent, 1),
                "memory_used_mb":  round(vm.used  / 1024**2),
                "memory_total_mb": round(vm.total / 1024**2),
                "disk_percent":    round(disk.percent, 1),
                "disk_free_gb":    round(disk.free / 1024**3, 2),
                "temperature":     _get_temperature(),
                "uptime_s":        round(time.time() - psutil.boot_time()),
                "load_avg":        list(psutil.getloadavg()),
                "z9":              z9_snap,
                "optimizer":       _optimizer_snap(_optimizer),
                "llm":             llm_snap,
                "memory_count":    len(_memory),
                "ts":              time.time(),
            })
        except Exception as exc:
            log.error(f"Status error: {exc}")
            return jsonify({"error": str(exc)}), 500

    # ─────────────────────────────────────────────────────────
    # FILE SYSTEM
    # ─────────────────────────────────────────────────────────

    @app.route("/api/files/list")
    def files_list():
        raw_path = request.args.get("path", str(Path.home()))
        try:
            p = Path(raw_path).expanduser().resolve()
            if not p.exists():
                return jsonify({"error": f"Path not found: {p}"}), 404
            file_agent = _dispatcher.agents["file"]
            result     = file_agent.execute(str(p), "list")
            parts      = list(p.parts)
            crumbs     = []
            for i, part in enumerate(parts):
                full = str(Path(*parts[:i+1])) if parts[:i+1] else "/"
                crumbs.append({"name": part or "/", "full": full})
            return jsonify({
                "path":       str(p),
                "items":      result.get("listing", []),
                "breadcrumb": crumbs,
                "count":      result.get("count", 0),
                "success":    result.get("success", False),
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/files/preview")
    def files_preview():
        raw_path  = request.args.get("path", "")
        max_chars = int(request.args.get("max", 60000))
        try:
            p          = Path(raw_path).expanduser().resolve()
            file_agent = _dispatcher.agents["file"]
            result     = file_agent.execute(str(p), "read")
            content    = result.get("content", "")
            truncated  = len(content) > max_chars
            return jsonify({
                "path":      str(p),
                "content":   content[:max_chars],
                "truncated": truncated,
                "success":   result.get("success", False),
                "error":     result.get("error"),
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/files/write", methods=["POST"])
    def files_write():
        data    = request.get_json(force=True, silent=True) or {}
        path    = data.get("path", "")
        content = data.get("content", "")
        try:
            result = _dispatcher.agents["file"].execute(path, "write", content)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/files/delete", methods=["POST"])
    def files_delete():
        data = request.get_json(force=True, silent=True) or {}
        path = data.get("path", "")
        if not path:
            return jsonify({"error": "Path required"}), 400
        try:
            result = _dispatcher.agents["file"].execute(path, "delete")
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/files/mkdir", methods=["POST"])
    def files_mkdir():
        data = request.get_json(force=True, silent=True) or {}
        path = data.get("path", "")
        if not path:
            return jsonify({"error": "Path required"}), 400
        try:
            result = _dispatcher.agents["file"].execute(path, "mkdir")
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/files/stat")
    def files_stat():
        raw_path = request.args.get("path", "")
        try:
            p      = Path(raw_path).expanduser().resolve()
            result = _dispatcher.agents["file"].execute(str(p), "stat")
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/files/rename", methods=["POST"])
    def files_rename():
        data     = request.get_json(force=True, silent=True) or {}
        src_path = data.get("src", "")
        dst_name = data.get("dst", "")
        if not src_path or not dst_name:
            return jsonify({"error": "src and dst required"}), 400
        try:
            src  = Path(src_path).expanduser().resolve()
            dst  = src.parent / dst_name
            src.rename(dst)
            return jsonify({"success": True, "renamed": str(dst)})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ─────────────────────────────────────────────────────────
    # DEDICATED SHELL (safe, with ShellGuard)
    # ─────────────────────────────────────────────────────────

    @app.route("/api/shell", methods=["POST", "OPTIONS"])
    def shell_exec():
        if request.method == "OPTIONS":
            return jsonify({}), 200
        data    = request.get_json(force=True, silent=True) or {}
        command = (data.get("command") or "").strip()
        timeout = int(data.get("timeout", CONFIG.get("shell", {}).get("timeout", 30)))
        if not command:
            return jsonify({"error": "Command required"}), 400
        try:
            result = _dispatcher.agents["system"].execute(command, timeout=timeout)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ─────────────────────────────────────────────────────────
    # MEMORY
    # ─────────────────────────────────────────────────────────

    @app.route("/api/memory/recall")
    def memory_recall():
        query = request.args.get("q", "").strip()
        k     = min(int(request.args.get("k", 5)), 20)
        if not query:
            return jsonify({"error": "Query required"}), 400
        try:
            results = _memory.recall(query, k=k)
            return jsonify({"results": results, "query": query, "k": k})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/memory/count")
    def memory_count():
        return jsonify({"count": len(_memory)})

    # ─────────────────────────────────────────────────────────
    # OPTIMIZER
    # ─────────────────────────────────────────────────────────

    @app.route("/api/optimizer/status")
    def optimizer_status():
        if not _optimizer:
            return jsonify({"available": False})
        return jsonify({"available": True, **_optimizer.summary()})

    @app.route("/api/optimizer/config", methods=["GET", "POST"])
    def optimizer_config():
        if not _optimizer:
            return jsonify({"available": False})
        if request.method == "POST":
            data = request.get_json(force=True, silent=True) or {}
            with _optimizer._lock:
                for k, v in data.items():
                    if k in _optimizer.config:
                        _optimizer.config[k] = float(v)
                _optimizer._clamp()
                _optimizer._save_config()
        return jsonify(_optimizer.current_params)

    # ─────────────────────────────────────────────────────────
    # LLM
    # ─────────────────────────────────────────────────────────

    @app.route("/api/llm/models")
    def llm_models():
        if not _llm:
            return jsonify({"available": False, "models": []})
        return jsonify({"available": _llm.is_available, "models": _llm.available_models()})

    @app.route("/api/llm/chat", methods=["POST"])
    def llm_chat():
        data    = request.get_json(force=True, silent=True) or {}
        prompt  = (data.get("prompt") or "").strip()
        model   = data.get("model", "auto")
        sys_p   = data.get("system")
        session = data.get("session_id")
        if not prompt:
            return jsonify({"error": "Empty prompt"}), 400
        if not _llm:
            return jsonify({"reply": "[Ollama not available]", "model": "none"})
        reply = _llm.route(prompt, model=model, system_prompt=sys_p, session_id=session)
        return jsonify({"reply": reply, "model": model})

    # ─────────────────────────────────────────────────────────
    # NETWORK
    # ─────────────────────────────────────────────────────────

    @app.route("/api/network")
    def network():
        try:
            hostname = socket.gethostname()
            ip       = socket.gethostbyname(hostname)
            ifaces   = {}
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ifaces[name] = addr.address
            stats = psutil.net_io_counters(pernic=False)
            return jsonify({
                "hostname":    hostname,
                "ip":          ip,
                "interfaces":  ifaces,
                "bytes_sent":  stats.bytes_sent,
                "bytes_recv":  stats.bytes_recv,
                "connected":   True,
            })
        except Exception as exc:
            return jsonify({"connected": False, "error": str(exc)})

    # ─────────────────────────────────────────────────────────
    # PICONNECT (local network node discovery)
    # ─────────────────────────────────────────────────────────

    @app.route("/api/piconnect")
    def piconnect():
        """
        Discover other Raspberry Pi / Linux nodes on the local subnet.
        Returns a list of reachable hosts.  Uses a quick ARP/ping sweep.
        On the Pi, `arp -a` gives a fast result.
        """
        try:
            r = subprocess.run(
                ["arp", "-a"],
                capture_output=True, text=True, timeout=5,
            )
            lines = r.stdout.strip().splitlines()
            nodes = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0].strip("()")
                    ip   = parts[1].strip("()")
                    if ip and ip not in ("incomplete", "<incomplete>"):
                        nodes.append({"name": name, "ip": ip, "status": "reachable"})
            # Always include self
            hostname = socket.gethostname()
            my_ip    = socket.gethostbyname(hostname)
            self_node = {"name": hostname, "ip": my_ip, "status": "self"}
            if not any(n["ip"] == my_ip for n in nodes):
                nodes.insert(0, self_node)
            return jsonify({
                "online": len(nodes),
                "nodes":  nodes,
                "self":   self_node,
            })
        except Exception as exc:
            return jsonify({"online": 1, "nodes": [], "error": str(exc)})

    # ─────────────────────────────────────────────────────────
    # QR CODE GENERATION
    # ─────────────────────────────────────────────────────────

    @app.route("/api/qr")
    def qr_code():
        """Generate a QR code PNG for the Pi's current URL."""
        if not _HAS_QR:
            return jsonify({"error": "qrcode not installed — pip install qrcode pillow"}), 501
        data = request.args.get("data", "")
        if not data:
            try:
                ip   = socket.gethostbyname(socket.gethostname())
                port = int(CONFIG.get("web_ui", {}).get("port", 5000))
                data = f"http://{ip}:{port}"
            except Exception:
                data = "http://localhost:5000"
        try:
            import io as _io
            from flask import send_file as _sf
            img  = qrcode.make(data)
            buf  = _io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return _sf(buf, mimetype="image/png", download_name="metatron-qr.png")
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ─────────────────────────────────────────────────────────
    # AGENTS
    # ─────────────────────────────────────────────────────────

    @app.route("/api/agents")
    def agents():
        return jsonify({
            name: {
                "name":   getattr(agent, "name", name),
                "charge": getattr(agent, "charge", 0),
            }
            for name, agent in _dispatcher.agents.items()
        })

    # ─────────────────────────────────────────────────────────
    # CONFIG
    # ─────────────────────────────────────────────────────────

    @app.route("/api/config", methods=["GET", "POST"])
    def config_endpoint():
        if request.method == "POST":
            data = request.get_json(force=True, silent=True) or {}
            CONFIG.update(data)
            try:
                CONFIG_PATH.write_text(json.dumps(CONFIG, indent=2))
            except Exception:
                pass
        return jsonify(CONFIG)

    # ─────────────────────────────────────────────────────────
    # HEALTH
    # ─────────────────────────────────────────────────────────

    @app.route("/api/health")
    def health():
        return jsonify({
            "status":    "ok",
            "version":   "3.1",
            "z9":        "operational",
            "optimizer": _optimizer.running if _optimizer else False,
            "llm":       _llm.is_available  if _llm       else False,
            "ts":        time.time(),
        })

    # ─────────────────────────────────────────────────────────
    # ERROR HANDLERS
    # ─────────────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "code": 404}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": str(e), "code": 500}), 500

    return app


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _sse(data: Dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _safe_serialize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, torch.Tensor):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (int, float, bool, str)) or obj is None:
        return obj
    return str(obj)


def _get_temperature() -> Any:
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


def _optimizer_snap(opt) -> Dict:
    if not opt:
        return {}
    return {
        "running":    opt.running,
        "last_error": float(list(opt.performance_history)[-1])
                      if opt.performance_history else 0.0,
        "config":     opt.current_params,
        "steps":      opt.step_count,
    }


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    for d in ("logs", "checkpoints", "config", "templates"):
        Path(d).mkdir(exist_ok=True)

    default = Path("config/metatron_config.default.json")
    if not CONFIG_PATH.exists() and default.exists():
        import shutil
        shutil.copy(default, CONFIG_PATH)

    log.info("=" * 60)
    log.info("  METATRON DESKTOP v3.1")
    log.info("  ℤ₉ Agentic Transformer Desktop — Raspberry Pi 500")
    log.info(f"  ε = {CONFIG['z9']['epsilon']}  λ = {CONFIG['z9']['lambda_hphi']}")
    log.info("=" * 60)

    app  = create_app()
    host = CONFIG.get("web_ui", {}).get("host", "0.0.0.0")
    port = int(CONFIG.get("web_ui", {}).get("port", 5000))

    log.info(f"  Server:  http://{host}:{port}")
    log.info(f"  QR code: http://{host}:{port}/api/qr")
    log.info("  Press Ctrl-C to stop")

    try:
        app.run(host=host, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        log.info("Shutting down METATRON DESKTOP…")
