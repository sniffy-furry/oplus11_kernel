#!/usr/bin/env python3
"""The tree carries KernelSU hook generations that do not match ReSukiSU's SUSFS inline-hook API
(ksu_handle_stat/faccessat take struct filename**, ksu_handle_sys_read takes 3 args; hooks are patched in at runtime).
Drop those stale in-tree hooks. Usage: fix_ksu_hooks.py <src>"""
import re, sys
root = sys.argv[1].rstrip("/")
RULES = {
 "fs/stat.c": [
  r'^[ \t]*extern int ksu_handle_stat\(.*\);\n',
  r'\n\tif \(static_branch_likely\(&ksu_su_compat_enabled\)\) \{\n\t\tif \(unlikely\(__ksu_is_allow_uid_for_current\(current_uid\(\)\.val\)\)\)\n\t\t\tksu_handle_stat\(&dfd, &filename, &flags\);\n\t\}\n',
  r'\n#ifdef CONFIG_KSU_SUSFS\n\tstruct filename \*fname = NULL;\n#endif\n',
 ],
 "fs/open.c": [
  r'^extern int ksu_handle_faccessat\([^;]*\);\n',
  r'\n\tif \(static_branch_likely\(&ksu_su_compat_enabled\)\) \{\n\t\tif \(unlikely\(__ksu_is_allow_uid_for_current\(current_uid\(\)\.val\)\)\)\n\t\t\tksu_handle_faccessat\(&dfd, &filename, &mode, NULL\);\n\t\}\n',
 ],
 "fs/read_write.c": [
  r'^extern __attribute__\(\(cold\)\) void ksu_handle_sys_read\(unsigned int fd\);\n',
  r'\n#ifdef CONFIG_KSU_SUSFS\n\tif \(static_branch_unlikely\(&ksu_is_init_rc_hook_enabled\)\)\n\t\tksu_handle_sys_read\(fd\);\n#endif\n',
 ],
}
for rel, pats in RULES.items():
    p = root + "/" + rel; s = open(p).read(); o = len(s)
    for pat in pats: s = re.sub(pat, "\n" if pat.startswith(r"\n") else "", s, flags=re.M)
    open(p, "w").write(s)
    left = len(re.findall(r"ksu_handle_(stat|faccessat|sys_read)\b", s))
    print("%s: removed %d bytes, leftover refs: %d" % (rel, o - len(s), left))
    assert left == 0, rel
