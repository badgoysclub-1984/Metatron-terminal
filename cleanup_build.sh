#!/bin/bash
MNT_DIR="/home/badgoysclub/metatron-os-v3/build_tmp/mnt"

if mount | grep -q "$MNT_DIR/dev/pts"; then umount "$MNT_DIR/dev/pts"; fi
if mount | grep -q "$MNT_DIR/dev"; then umount "$MNT_DIR/dev"; fi
if mount | grep -q "$MNT_DIR/proc"; then umount "$MNT_DIR/proc"; fi
if mount | grep -q "$MNT_DIR/sys"; then umount "$MNT_DIR/sys"; fi
if mount | grep -q "$MNT_DIR/boot/firmware"; then umount "$MNT_DIR/boot/firmware"; fi
if mount | grep -q "$MNT_DIR"; then umount "$MNT_DIR"; fi

# Detach loop devices
for dev in $(losetup -j /home/badgoysclub/metatron-os-v3/build_tmp/metatron-os-v3.1.img | cut -d: -f1); do
    losetup -d "$dev"
done
