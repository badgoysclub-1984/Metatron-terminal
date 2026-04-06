#!/bin/bash
# METATRON QUANTUM OS v3.1 — One-click installer for Raspberry Pi 500
# Usage: chmod +x install.sh && ./install.sh
set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      METATRON QUANTUM OS v3.1 — Installer               ║"
echo "║      ℤ₉ Agentic Transformer Desktop · Raspberry Pi 500   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── System packages ────────────────────────────────────────────
echo "🔧 [1/5] Installing system packages…"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3-pip python3-venv git curl \
  tesseract-ocr libtesseract-dev \
  ffmpeg alsa-utils pulseaudio \
  arp-scan net-tools \
  2>/dev/null || true

# ── Python venv ────────────────────────────────────────────────
echo "🐍 [2/5] Creating Python virtual environment…"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip --quiet

# ── Python dependencies ────────────────────────────────────────
echo "📦 [3/5] Installing Python packages…"
# Core packages first (smaller, faster)
pip install flask psutil numpy requests beautifulsoup4 python-dotenv --quiet

# PyTorch for Pi (CPU-only wheel)
echo "    → Installing PyTorch (CPU-only, may take a few minutes)…"
pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet

# ML packages
pip install faiss-cpu sentence-transformers ollama --quiet

# Utilities
pip install "qrcode[pil]" pillow pytesseract --quiet

# ── Config ────────────────────────────────────────────────────
echo "⚙️  [4/5] Setting up configuration…"
mkdir -p config logs checkpoints
if [ ! -f "config/metatron_config.json" ] && [ -f "config/metatron_config.default.json" ]; then
  cp config/metatron_config.default.json config/metatron_config.json
  echo "    → Config initialised from defaults."
fi

# ── Ollama + LLMs ─────────────────────────────────────────────
echo "🤖 [5/5] Installing Ollama and pulling LLMs…"
if ! command -v ollama &> /dev/null; then
  echo "    → Installing Ollama…"
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "    → Ollama already installed: $(ollama --version)"
fi

echo "    → Pulling Gemma4-abliterated (charge 0 / general)…"
ollama pull huihui_ai/gemma3-abliterated:4b || true

echo "    → Pulling Qwen2.5-Coder (charge 6 / code)…"
ollama pull qwen2.5-coder:3b || true

echo "    → Pulling DeepSeek-Coder-v2 (charge 3 / reasoning)…"
ollama pull deepseek-coder-v2:lite || true

# ── Custom Modelfile (ℤ₉-tuned system prompt) ─────────────────
if [ ! -f "Modelfile" ]; then
  echo "    → Generating Modelfile for z9-gemma-abliterated…"
  python3 z9_qat_training.py export 2>/dev/null || true
fi
if [ -f "Modelfile" ]; then
  ollama create z9-gemma-abliterated -f Modelfile 2>/dev/null || true
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅  METATRON QUANTUM OS v3.1 installed successfully!    ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Run:  source venv/bin/activate                          ║"
echo "║        python quantum_desktop.py                         ║"
echo "║  Open: http://localhost:5000                             ║"
echo "║  QR:   http://localhost:5000/api/qr                      ║"
echo "║                                                          ║"
echo "║  Optional training:                                      ║"
echo "║    python z9_qat_training.py          # quick dummy      ║"
echo "║    python z9_qat_training.py full     # full HF dataset  ║"
echo "╚══════════════════════════════════════════════════════════╝"
