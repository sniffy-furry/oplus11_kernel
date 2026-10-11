#!/bin/bash
# Fetch the exact Android clang (default r563880c) used by the stock kernel. Fails loudly if not found.
set -uo pipefail
VER="${1:-clang-r563880c}"; DEST="${2:-$HOME/aclang}"
G=https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86
mkdir -p "$DEST" && cd "$DEST"
echo "== looking for $VER on googlesource"
refs=$(git ls-remote --heads --tags "$G" 2>/dev/null | awk '{print $2}' | grep -E 'android1[4-9]|^refs/heads/(main|master)$|android-1[4-9]' | sort -Vr)
[ -z "$refs" ] && echo "ls-remote returned nothing (blocked?)"
for ref in refs/heads/main $refs; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$G/+/$ref/$VER/AndroidVersion.txt?format=TEXT")
  [ "$code" = 200 ] || continue
  echo "found $VER in $ref -> downloading"
  if curl -fL --retry 3 --max-time 1500 -o c.tgz "$G/+archive/$ref/$VER.tar.gz" && tar xzf c.tgz && [ -x bin/clang ]; then
    echo "OK from googlesource $ref"; bin/clang --version | head -2; echo "$DEST/bin" > "$DEST/.pathfile"; exit 0
  fi
done
echo "== googlesource failed, trying LineageOS GitHub mirror (sparse)"
for br in lineage-23.2 lineage-23.1 lineage-23.0 lineage-22.2 lineage-22.1; do
  rm -rf mirror && git clone -q --depth=1 --filter=blob:none --sparse -b "$br" https://github.com/LineageOS/android_prebuilts_clang_host_linux-x86 mirror 2>/dev/null || continue
  (cd mirror && git sparse-checkout set "$VER" 2>/dev/null)
  if [ -x "mirror/$VER/bin/clang" ]; then echo "OK from LineageOS $br"; "mirror/$VER/bin/clang" --version | head -2; echo "$DEST/mirror/$VER/bin" > "$DEST/.pathfile"; exit 0; fi
done
echo "FATAL: could not obtain $VER"; exit 1
