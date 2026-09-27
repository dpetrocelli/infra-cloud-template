#!/bin/bash
# Class 1 demo: mount the persistent disk, install Docker, run the servicio
# patron image with its state on that disk. Kill the VM, keep the disk, the
# state is still there.
set -euo pipefail

DEVICE="/dev/disk/by-id/google-${disk_device_name}"
MOUNT_POINT="/mnt/disks/datos"

if ! blkid "$DEVICE" >/dev/null 2>&1; then
  mkfs.ext4 -F "$DEVICE"
fi

mkdir -p "$MOUNT_POINT"
mount "$DEVICE" "$MOUNT_POINT" || true
echo "$DEVICE $MOUNT_POINT ext4 discard,defaults,nofail 0 2" >> /etc/fstab

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

docker rm -f ${container_name} >/dev/null 2>&1 || true
docker run -d --name ${container_name} --restart unless-stopped \
  -p ${app_port}:${app_port} \
  -e DATA_DIR=/data \
  -e PORT=${app_port} \
  -v "$MOUNT_POINT":/data \
  ${image}
