#!/usr/bin/env python3
"""Classify every Mach-O file and dyld shared cache under ROOT by CPU.

Usage: census.py ROOT OUT.tsv

OUT.tsv columns: bucket, archs, size, path (relative to ROOT)
bucket: universal (arm + Intel slices), x86-only, arm-only, other,
        or dyld-cache
"""
import os
import struct
import sys

X86 = ("x86_64", "x86_64h", "i386")


def cpu_name(ct, st):
    ct &= 0xFFFFFFFF
    st &= 0xFFFFFFFF
    if ct == 0x0100000C:
        # Exact names only for subtypes we can vouch for; anything else is
        # reported raw so a second tool can name it.
        # 0x8000000c and 0xc0000002 named from Apple's lipo (verify run).
        return {0: "arm64", 1: "arm64v8", 2: "arm64e", 0x80000002: "arm64e",
                0xc0000002: "arm64e", 0x8000000c: "arm64e.x1"
                }.get(st, f"arm64:{st:#x}")
    if ct == 0x01000007:
        return "x86_64h" if (st & 0xFF) == 8 else "x86_64"
    named = {7: "i386", 12: "arm", 0x0200000C: "arm64_32",
             18: "ppc", 0x01000012: "ppc64"}.get(ct)
    # Keep the file. Dropping an unknown slice used to drop its Intel
    # siblings too, because a fat binary returned nothing if any slice
    # failed to name.
    return named or f"cpu:{ct:#x}/{st:#x}"


def classify(path):
    try:
        with open(path, "rb") as fh:
            h = fh.read(4096)
    except OSError:
        return None
    if len(h) < 16:
        return None
    if h.startswith(b"dyld_v1"):
        return "dyld-cache", [h[7:16].decode("ascii", "replace").strip("\x00 ")]
    magic = h[:4]
    if magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe"):
        return "thin", [cpu_name(*struct.unpack("<II", h[4:12]))]
    if magic in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
        n = struct.unpack(">I", h[4:8])[0]
        if not 0 < n <= 16:  # Java class files share this magic
            return None
        step = 20 if magic == b"\xca\xfe\xba\xbe" else 32
        archs = []
        for i in range(n):
            o = 8 + i * step
            if o + 8 > len(h):
                return None
            archs.append(cpu_name(*struct.unpack(">II", h[o:o + 8])))
        return "fat", archs
    return None


def bucket(kind, archs):
    if kind == "dyld-cache":
        return "dyld-cache"
    x = any(a in X86 for a in archs)
    r = any(a.startswith("arm") for a in archs)
    if x and r:
        return "universal"
    if x:
        return "x86-only"
    if r:
        return "arm-only"
    return "other"


def main():
    root, out = sys.argv[1], sys.argv[2]
    counts = {}
    with open(out, "w", encoding="utf-8") as fo:
        for d, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(d, f)
                if os.path.islink(p) or not os.path.isfile(p):
                    continue
                c = classify(p)
                if not c:
                    continue
                b = bucket(*c)
                counts[b] = counts.get(b, 0) + 1
                rel = os.path.relpath(p, root)
                fo.write(f"{b}\t{','.join(c[1])}\t{os.path.getsize(p)}\t{rel}\n")
    for b in sorted(counts):
        print(f"{b}: {counts[b]}")


if __name__ == "__main__":
    main()
