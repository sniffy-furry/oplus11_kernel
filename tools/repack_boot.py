#!/usr/bin/env python3
"""Replace the kernel inside an Android boot image (header v4), keep everything else.
usage: repack_boot.py stock_boot.img new_Image out_boot.img
Drops the AVB footer (bootloader is unlocked; it would be stale anyway)."""
import struct, sys
PAGE = 4096
def up(n): return (n + PAGE - 1) // PAGE * PAGE
src, kern, out = sys.argv[1:4]
d = open(src, 'rb').read()
k = open(kern, 'rb').read()
assert d[:8] == b'ANDROID!', 'not an Android boot image'
ksz, rsz = struct.unpack_from('<II', d, 8)
hver = struct.unpack_from('<I', d, 40)[0]
assert hver == 4, f'header v{hver}: only v4 supported'
sig = struct.unpack_from('<I', d, 1580)[0]
rest_off = PAGE + up(ksz)                      # ramdisk (+ boot signature) follow the kernel
rest = d[rest_off: rest_off + up(rsz) + up(sig)]
hdr = bytearray(d[:PAGE]); struct.pack_into('<I', hdr, 8, len(k))
img = bytes(hdr) + k + b'\0' * (up(len(k)) - len(k)) + rest
open(out, 'wb').write(img)
print(f'old kernel {ksz} -> new {len(k)}, ramdisk {rsz}, sig {sig}, out {len(img)} bytes')
