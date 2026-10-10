#!/bin/bash
# Builds static aarch64 busybox + kexec and writes stage1/initramfs.list (absolute paths)
set -euo pipefail
W="${1:?workdir}"; REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$W" && cd "$W"
sudo apt-get install -y -q gcc-aarch64-linux-gnu make bzip2 xz-utils >/dev/null
export CROSS_COMPILE=aarch64-linux-gnu-
curl -fsSL https://busybox.net/downloads/busybox-1.36.1.tar.bz2 | tar xj
( cd busybox-1.36.1 && make defconfig >/dev/null \
  && sed -i 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/;s/^CONFIG_TC=y/# CONFIG_TC is not set/' .config \
  && make ARCH=arm64 olddefconfig >/dev/null && grep -E '^CONFIG_STATIC=y' .config \
  && make ARCH=arm64 -j"$(nproc)" busybox >/dev/null )
curl -fsSL https://www.kernel.org/pub/linux/utils/kernel/kexec/kexec-tools-2.0.29.tar.xz | tar xJ
( cd kexec-tools-2.0.29 && ./configure --host=aarch64-linux-gnu LDFLAGS=-static >/dev/null && make -j"$(nproc)" >/dev/null )
BB="$W/busybox-1.36.1/busybox"; KX="$W/kexec-tools-2.0.29/build/sbin/kexec"
file "$BB" "$KX"
aarch64-linux-gnu-strip "$BB" "$KX"
sed "s|@BB@|$BB|;s|@KEXEC@|$KX|;s|@HOOK@|$REPO/initramfs/linux_hook|" "$REPO/initramfs/initramfs.list.in" > "$W/initramfs.list"
cat "$W/initramfs.list"
