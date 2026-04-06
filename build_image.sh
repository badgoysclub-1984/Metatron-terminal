#!/bin/bash
# ==============================================================================
# METATRON OS v3.1 IMAGE BUILDER
# ==============================================================================
# This script downloads the official Raspberry Pi OS Desktop (64-bit),
# expands it, chroots into it, installs all Metatron OS dependencies,
# sets up systemd services to launch the AI overlay on boot,
# and prepares the final image to be flashed to an SD card.
# ==============================================================================

set -e

# Configuration
IMAGE_URL="https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2024-11-19/2024-11-19-raspios-bookworm-arm64.img.xz"
IMAGE_XZ="raspios.img.xz"
FINAL_IMG="metatron-os-v3.1.img"
WORKDIR="/home/badgoysclub/metatron-os-v3"
BUILD_DIR="$WORKDIR/build_tmp"
MNT_DIR="$BUILD_DIR/mnt"
METATRON_SRC="/home/badgoysclub/metatron-os-v3"

# Ensure we are running with root privileges where needed
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (or with sudo)"
  exit 1
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "==== 1. Downloading Official Raspberry Pi OS Base ===="
if [ ! -f "$IMAGE_XZ" ] && [ ! -f "$FINAL_IMG" ]; then
    wget --progress=dot:giga -O "$IMAGE_XZ" "$IMAGE_URL"
fi

if [ ! -f "$FINAL_IMG" ]; then
    echo "==== 2. Extracting Image ===="
    xz -d -c "$IMAGE_XZ" > "$FINAL_IMG"
fi

echo "==== 3. (Skipping) Expanding Image for AI Models (Already 22GB) ===="
# 16GB is enough for Ollama models + PyTorch + future expansion
# dd if=/dev/zero bs=1M count=16000 >> "$FINAL_IMG"
# parted "$FINAL_IMG" resizepart 2 100%

echo "==== 4. Setting up Loopback & Mounting ===="
LOOP_DEV=$(losetup -P -f --show "$FINAL_IMG")
echo "Mounted image at $LOOP_DEV"

# Resize filesystem
e2fsck -f "${LOOP_DEV}p2" || true
resize2fs "${LOOP_DEV}p2"

mkdir -p "$MNT_DIR"
mount "${LOOP_DEV}p2" "$MNT_DIR"
mount "${LOOP_DEV}p1" "$MNT_DIR/boot/firmware"

# Prepare Chroot environment
mount --bind /dev "$MNT_DIR/dev"
mount --bind /sys "$MNT_DIR/sys"
mount --bind /proc "$MNT_DIR/proc"
mount --bind /dev/pts "$MNT_DIR/dev/pts"
cp /etc/resolv.conf "$MNT_DIR/etc/resolv.conf"

echo "==== 5. Creating Default User (pi / raspberry) ===="
# Bookworm requires userconf.txt for the default user
PASS_HASH=$(echo "raspberry" | openssl passwd -6 -stdin)
echo "pi:$PASS_HASH" > "$MNT_DIR/boot/firmware/userconf.txt"
touch "$MNT_DIR/boot/firmware/ssh"

# Ensure 'pi' user exists inside chroot for setup
chroot "$MNT_DIR" useradd -m -s /bin/bash pi || true
echo "pi:raspberry" | chroot "$MNT_DIR" chpasswd

echo "==== 6. Injecting Metatron OS Base Files ===="
mkdir -p "$MNT_DIR/home/pi/metatron-os-v3"
# Copy everything from current repo into the image EXCEPT large/unnecessary files
rsync -a \
    --exclude 'build_tmp' \
    --exclude 'venv' \
    --exclude '.git' \
    --exclude '.pytest_cache' \
    --exclude '*.img' \
    --exclude '*.xz' \
    --exclude 'metatron.log' \
    --exclude 'build.log' \
    "$METATRON_SRC/" "$MNT_DIR/home/pi/metatron-os-v3/"
chroot "$MNT_DIR" chown -R 1000:1000 /home/pi/metatron-os-v3

echo "==== 7. Setting up Environment and Installing Dependencies (Chroot) ===="
# We create a script to execute inside the chroot
cat << 'EOF' > "$MNT_DIR/tmp/chroot_setup.sh"
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
export HOME=/home/pi

# Update and install system dependencies
apt-get update
apt-get install -y python3-pip python3-venv git curl tesseract-ocr libtesseract-dev ffmpeg alsa-utils pulseaudio arp-scan net-tools sudo grim wtype ydotool xdotool scrot

# Ensure pi is in sudoers
usermod -aG sudo pi

# Switch to 'pi' user context for Python venv
cd /home/pi/metatron-os-v3
sudo -u pi bash -c "python3 -m venv venv"
sudo -u pi bash -c "source venv/bin/activate && pip install --upgrade pip"
sudo -u pi bash -c "source venv/bin/activate && pip install --no-cache-dir flask psutil numpy requests beautifulsoup4 python-dotenv torch --index-url https://download.pytorch.org/whl/cpu"
sudo -u pi bash -c "source venv/bin/activate && pip install --no-cache-dir faiss-cpu sentence-transformers ollama qrcode[pil] pillow pytesseract"

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pre-pull AI models
# Start Ollama in background
ollama serve > /var/log/ollama.log 2>&1 &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
for i in {1..30}; do
    if ollama list >/dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    sleep 2
done

# Pulling models
echo "Pulling models (this may take a while)..."
sudo -u pi bash -c "ollama pull huihui_ai/gemma3-abliterated:4b" || true
sudo -u pi bash -c "ollama pull qwen2.5-coder:3b" || true

# Generate Custom Modelfile if exists
if [ -f "/home/pi/metatron-os-v3/Modelfile" ]; then
    echo "Creating custom Z9 model..."
    sudo -u pi bash -c "ollama create z9-gemma-abliterated -f /home/pi/metatron-os-v3/Modelfile" || true
fi

kill $OLLAMA_PID || true
# Ensure models directory is owned by pi
chown -R pi:pi /home/pi/.ollama 2>/dev/null || true

# Setup Autostart Services
# 1. Metatron Backend systemd service
cat << 'SVC' > /etc/systemd/system/metatron-desktop.service
[Unit]
Description=Metatron Desktop AI Overlay Backend
After=network.target graphical.target ollama.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/metatron-os-v3
Environment=PATH=/home/pi/metatron-os-v3/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/pi/metatron-os-v3/venv/bin/python quantum_desktop.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
SVC
systemctl enable metatron-desktop.service

# 2. GUI Autostart (Chromium Kiosk mode on Desktop)
mkdir -p /home/pi/.config/autostart
cat << 'DSK' > /home/pi/.config/autostart/metatron-overlay.desktop
[Desktop Entry]
Type=Application
Name=Metatron AI Overlay
Exec=chromium-browser --start-fullscreen http://localhost:5000
NoDisplay=false
Hidden=false
X-GNOME-Autostart-enabled=true
DSK
chown -R pi:pi /home/pi/.config

EOF

chmod +x "$MNT_DIR/tmp/chroot_setup.sh"
echo "Running chroot setup... This will download PyTorch and AI models (may take 1-2 hours depending on connection)."
chroot "$MNT_DIR" /tmp/chroot_setup.sh

echo "==== 8. Cleanup and Finalization ===="
rm -f "$MNT_DIR/tmp/chroot_setup.sh"
sync

umount "$MNT_DIR/dev/pts"
umount "$MNT_DIR/proc"
umount "$MNT_DIR/sys"
umount "$MNT_DIR/dev"
umount "$MNT_DIR/boot/firmware"
umount "$MNT_DIR"

losetup -d "$LOOP_DEV"

# Move the final image out of the tmp build folder
mv "$FINAL_IMG" "$WORKDIR/"
echo "======================================================================"
echo "✅  BUILD COMPLETE!"
echo "Your bootable Metatron OS image is ready at: $WORKDIR/$FINAL_IMG"
echo "You can now flash this image to an SD card using Raspberry Pi Imager or 'dd'."
echo "======================================================================"
