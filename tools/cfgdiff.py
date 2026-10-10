#!/usr/bin/env python3
"""Print options whose value differs between the built .config and the stock phone config."""
import gzip, re, sys
def load(p):
    o = gzip.open if p.endswith(".gz") else open
    d = {}
    for l in o(p, "rt"):
        l = l.strip()
        m = re.match(r"(CONFIG_\w+)=(.*)", l)
        if m: d[m[1]] = m[2]
        m = re.match(r"# (CONFIG_\w+) is not set", l)
        if m: d[m[1]] = "n"
    return d
mine, stock = load(sys.argv[1]), load(sys.argv[2])
diff = [(k, stock.get(k, "<absent>"), mine.get(k, "<absent>")) for k in sorted(set(mine) | set(stock)) if mine.get(k, "<absent>") != stock.get(k, "<absent>")]
print("options differing from stock: %d" % len(diff))
print("%-48s %-10s %s" % ("option", "stock", "built"))
for k, s, m in diff[:150]: print("%-48s %-10s %s" % (k, s, m))
