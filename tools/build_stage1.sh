#!/bin/bash
# Builds static aarch64 busybox + keystate and writes stage1/initramfs.list (absolute paths)
set -euo pipefail
W="${1:?workdir}"; REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$W" && cd "$W"
sudo apt-get install -y -q gcc-aarch64-linux-gnu make bzip2 xz-utils >/dev/null
export CROSS_COMPILE=aarch64-linux-gnu-
curl -fsSL https://busybox.net/downloads/busybox-1.36.1.tar.bz2 | tar xj
( cd busybox-1.36.1 && make defconfig >/dev/null \
  && sed -i 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/;s/^CONFIG_TC=y/# CONFIG_TC is not set/' .config \
  && grep -E '^CONFIG_STATIC=y' .config \
  && make ARCH=arm64 -j"$(nproc)" busybox >/dev/null )
aarch64-linux-gnu-gcc -static -O2 -o "$W/keystate" "$REPO/initramfs/keystate.c"
BB="$W/busybox-1.36.1/busybox"; KS="$W/keystate"
file "$BB" "$KS"
aarch64-linux-gnu-strip "$BB" "$KS"
sed "s|@BB@|$BB|;s|@KS@|$KS|;s|@HOOK@|$REPO/initramfs/linux_hook|" "$REPO/initramfs/initramfs.list.in" > "$W/initramfs.list"
cat "$W/initramfs.list"
