#!/usr/bin/env python3
"""Remove SUSFS hunks that the upstream tree applied twice (same #ifdef block repeated close together).
Usage: dedupe_susfs.py <kernel_src_dir>   (prints what it changed)"""
import os, re, subprocess, sys

OPEN = re.compile(r'^\s*#\s*(if|ifdef|ifndef)\b')
END = re.compile(r'^\s*#\s*endif\b')
KEY = "KSU_SUSFS"
GAP = 12  # max lines between the two copies

def blocks(lines):
    """top-level preprocessor blocks mentioning KSU_SUSFS in their opening line: (start, end_inclusive)"""
    out, i, n = [], 0, len(lines)
    while i < n:
        if OPEN.match(lines[i]) and KEY in lines[i]:
            d, j = 0, i
            while j < n:
                if OPEN.match(lines[j]): d += 1
                elif END.match(lines[j]):
                    d -= 1
                    if d == 0: break
                j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out

def dedupe(path):
    try: lines = open(path, encoding="utf-8", errors="surrogateescape").read().split("\n")
    except Exception: return 0
    bl = blocks(lines); drop = set(); kept = []
    for (s, e) in bl:
        txt = "\n".join(l.strip() for l in lines[s:e+1])
        dup = False
        for (ks, ke, kt) in kept[-3:]:
            if kt == txt and s - ke <= GAP: dup = True; break
        if dup: drop.update(range(s, e+1))
        else: kept.append((s, e, txt))
    if not drop: return 0
    new = [l for k, l in enumerate(lines) if k not in drop]
    open(path, "w", encoding="utf-8", errors="surrogateescape").write("\n".join(new))
    return len(drop)

def main(root):
    files = subprocess.run(["grep", "-rIl", "--include=*.c", "--include=*.h", KEY, root],
                           capture_output=True, text=True).stdout.split()
    tot = 0
    for f in sorted(files):
        if "/KernelSU/" in f or "/susfs4ksu/" in f: continue
        n = dedupe(f)
        if n: print("deduped %3d lines: %s" % (n, os.path.relpath(f, root))); tot += n
    print("total removed lines:", tot)

if __name__ == "__main__":
    main(sys.argv[1])
