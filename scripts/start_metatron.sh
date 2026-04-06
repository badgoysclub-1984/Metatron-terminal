#!/bin/bash
# 🧿 METATRON DESKTOP — Boot Overlay Script
# v3.1 Hardlocked Edition

cd /home/badgoysclub/metatron-os-v3

# 1. Activate venv and start backend
source venv/bin/activate
python quantum_desktop.py > logs/startup.log 2>&1 &
BACKEND_PID=$!

# 2. Wait for backend to be ready (retry up to 30s)
for i in {1..30}; do
    if curl -s http://localhost:5000/api/health > /dev/null; then
        echo "🧿 Metatron Backend READY"
        break
    fi
    sleep 1
done

# 3. Launch UI in Chromium Kiosk Mode (Hardlocked)
# Using --kiosk to force full screen and disable escape
# --app=... to remove browser chrome
chromium-browser --kiosk --app=http://localhost:5000 --no-first-run --disable-infobars --window-position=0,0 --window-size=1920,1080 &

echo "🧿 Metatron Overlay Operational"
wait $BACKEND_PID
