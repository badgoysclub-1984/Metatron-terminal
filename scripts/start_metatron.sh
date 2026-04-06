#!/bin/bash
# 🧿 METATRON DESKTOP — Boot Overlay Script
# v3.1 Hardlocked Edition

cd /home/badgoysclub/metatron-os-v3

# 1. Activate venv and start backend
source venv/bin/activate

# Ensure Wayland environment is correctly set
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export GDK_BACKEND=wayland
export QT_QPA_PLATFORM=wayland

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

# 3. Launch UI in Chromium (Standard Mode)
# Removed --kiosk to allow window management
# --app=... to remove browser chrome
# Added --ozone-platform=wayland for native Wayland support
chromium --app=http://localhost:5000 \
    --no-first-run --disable-infobars \
    --window-position=100,100 --window-size=1280,720 \
    --ozone-platform=wayland \
    --enable-features=UseOzonePlatform \
    > logs/chromium.log 2>&1 &

echo "🧿 Metatron Overlay Operational"
wait $BACKEND_PID
