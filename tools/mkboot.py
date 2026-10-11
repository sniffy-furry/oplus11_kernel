#!/usr/bin/env python3
"""
mkboot.py - build a validly signed `boot` image for OnePlus 11 (salami) / AlphaDroid
with a different kernel, keeping everything else identical to stock.

Why this works: the stock boot image is signed with the PUBLIC AOSP key
testkey_rsa4096 (avb pubkey sha1 2597c218aae470a130f61162feaae70afd97f011), and
this script reproduces the stock AVB footer bit-for-bit when given the stock kernel.

usage:
  python3 mkboot.py STOCK_BOOT.img NEW_KERNEL_Image OUT.img PARTITION_SIZE_BYTES [--salt HEX]

  STOCK_BOOT.img  : the stock image (only its first 4096 bytes - the header - are used;
                    your bk_head.img / a full dump both work)
  NEW_KERNEL_Image: raw arm64 `Image` (not gzip), as built by the CI
  PARTITION_SIZE  : exact size of the boot_b partition, get it with:
                    su -c 'blockdev --getsize64 /dev/block/by-name/boot_b'

needs: python3 + the `openssl` binary (Termux: pkg install python openssl-tool)
"""
import hashlib, os, shutil, struct, subprocess, sys, tempfile, urllib.request

BASE = "https://raw.githubusercontent.com/LineageOS/android_external_avb/lineage-22.2/"
AVBTOOL_URL = BASE + "avbtool.py"
KEY_URL = BASE + "test/data/testkey_rsa4096.pem"
STOCK_KEY_SHA1 = "2597c218aae470a130f61162feaae70afd97f011"   # avb public key blob sha1 of stock
ROLLBACK_INDEX = "1785542400"                                  # same as stock (must not be lower)
PROPS = [  # same as stock
    "com.android.build.boot.os_version:16",
    "com.android.build.boot.fingerprint:OnePlus/alpha_salami/salami:16/BP4A.251205.006/eng.androi:userdebug/release-keys",
    "com.android.build.boot.security_patch:2026-05-01",
]
PAGE = 4096
HERE = os.path.dirname(os.path.abspath(__file__))


def die(msg):
    print("ERROR:", msg)
    sys.exit(1)


def fetch(url, dest):
    if not os.path.exists(dest):
        print("downloading", url)
        urllib.request.urlretrieve(url, dest)
    return dest


def run(*cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        die("command failed: %s\n%s" % (" ".join(cmd[:4]), r.stdout))
    return r.stdout


def main(argv):
    salt = None
    if "--salt" in argv:
        i = argv.index("--salt")
        salt = argv[i + 1]
        del argv[i:i + 2]
    if len(argv) != 4:
        print(__doc__)
        sys.exit(2)
    stock_path, kernel_path, out_path, part_size = argv[0], argv[1], argv[2], int(argv[3])

    avbtool = fetch(AVBTOOL_URL, os.path.join(HERE, "avbtool.py"))
    key = fetch(KEY_URL, os.path.join(HERE, "testkey_rsa4096.pem"))

    # the key must be the one stock is signed with
    with tempfile.TemporaryDirectory() as td:
        pub = os.path.join(td, "pub.bin")
        run(sys.executable, avbtool, "extract_public_key", "--key", key, "--output", pub)
        if hashlib.sha1(open(pub, "rb").read()).hexdigest() != STOCK_KEY_SHA1:
            die("downloaded key does not match the stock AVB key - refusing to continue")

        hdr = open(stock_path, "rb").read(PAGE)
        if hdr[:8] != b"ANDROID!" or struct.unpack_from("<I", hdr, 40)[0] != 4:
            die("stock image is not an Android boot image v4")
        kernel = open(kernel_path, "rb").read()
        if kernel[56:60] != b"ARMd":
            die("kernel is not a raw arm64 Image (expected 'ARMd' magic at offset 56; gzip/lz4 is not accepted)")

        # new header = stock header with only kernel_size changed
        hdr = hdr[:8] + struct.pack("<I", len(kernel)) + hdr[12:]
        data = hdr + kernel
        data += b"\0" * (-len(data) % PAGE)

        img = os.path.join(td, "boot.img")        # avbtool looks for <partition_name>.img when verifying
        open(img, "wb").write(data)
        cmd = [sys.executable, avbtool, "add_hash_footer", "--image", img,
               "--partition_size", str(part_size), "--partition_name", "boot",
               "--algorithm", "SHA256_RSA4096", "--key", key, "--rollback_index", ROLLBACK_INDEX]
        if salt:
            cmd += ["--salt", salt]
        for p in PROPS:
            cmd += ["--prop", p]
        run(*cmd)
        out = run(sys.executable, avbtool, "verify_image", "--image", img, "--key", key)
        print(out.strip())
        shutil.copyfile(img, out_path)

    sz = os.path.getsize(out_path)
    print("OK: %s  size=%d (partition=%d)  sha256=%s" % (
        out_path, sz, part_size, hashlib.sha256(open(out_path, "rb").read()).hexdigest()))
    print("Image part: %d bytes (stock was 45641728)." % (len(data)))


if __name__ == "__main__":
    main(sys.argv[1:])
