#!/usr/bin/env python3
"""Replace the kernel inside an Android boot image (header v4) and rebuild a valid AVB footer.

usage: repack_boot.py HEADER_OR_BOOT.img new_Image out.img [--vbmeta stock_vbmeta.bin --partition-size N]

Why the footer matters: the stock boot partition = image | embedded vbmeta blob (AVB0...) | zeros | 64-byte
AVBf footer at the very END of the partition. A bigger kernel must not overwrite that blob, otherwise the
bootloader cannot parse the vbmeta at all (hard failure -> bootloop). With --vbmeta/--partition-size the blob is
moved right behind the new image and the footer is rewritten; the signature stays valid, only the hash no longer
matches, which an unlocked bootloader tolerates (same state as a Magisk-patched boot image)."""
import struct, sys, argparse
PAGE = 4096
def up(n): return (n + PAGE - 1) // PAGE * PAGE
ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('kernel'); ap.add_argument('out')
ap.add_argument('--vbmeta'); ap.add_argument('--partition-size', type=int)
a = ap.parse_args()
d = open(a.src, 'rb').read()
k = open(a.kernel, 'rb').read()
assert d[:8] == b'ANDROID!', 'not an Android boot image'
ksz, rsz = struct.unpack_from('<II', d, 8)
hver = struct.unpack_from('<I', d, 40)[0]
assert hver == 4, f'header v{hver}: only v4 supported'
sig = struct.unpack_from('<I', d, 1580)[0]
if len(d) <= PAGE:
    assert rsz == 0 and sig == 0, 'header-only input needs a boot image without ramdisk/signature'
rest_off = PAGE + up(ksz)
rest = d[rest_off: rest_off + up(rsz) + up(sig)]
hdr = bytearray(d[:PAGE]); struct.pack_into('<I', hdr, 8, len(k))
img = bytes(hdr) + k + b'\0' * (up(len(k)) - len(k)) + rest
if a.vbmeta:
    vb = open(a.vbmeta, 'rb').read()
    assert vb[:4] == b'AVB0', 'vbmeta blob must start with AVB0'
    assert a.partition_size and a.partition_size % PAGE == 0
    assert len(img) + len(vb) <= a.partition_size - 64, 'image + vbmeta do not fit the partition'
    out = bytearray(a.partition_size)
    out[:len(img)] = img
    out[len(img):len(img) + len(vb)] = vb
    out[-64:] = struct.pack('>4sIIQQQ28x', b'AVBf', 1, 0, len(img), len(img), len(vb))
    img = bytes(out)
open(a.out, 'wb').write(img)
print(f'old kernel {ksz} -> new {len(k)}, ramdisk {rsz}, sig {sig}, out {len(img)} bytes' + (' (with AVB footer)' if a.vbmeta else ' (NO AVB footer)'))
