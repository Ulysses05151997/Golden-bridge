#!/usr/bin/env python3
"""Second instrument: compare census.py's reading of every file with
Apple's own `lipo -archs`.

Checks, for every Mach-O in CENSUS.tsv:
  1. the Intel slices (x86_64, x86_64h, i386) are exactly the same;
  2. both tools agree whether any arm slice is present;
and tallies how census.py's arm labels line up with lipo's names.

Usage: lipocheck.py ROOT CENSUS.tsv
"""
import collections
import os
import subprocess
import sys

X86 = {"x86_64", "x86_64h", "i386"}


def main():
    root, tsv = sys.argv[1], sys.argv[2]
    n = x86_ok = arm_ok = 0
    bad = []
    pairs = collections.Counter()
    with open(tsv, encoding="utf-8") as fh:
        for line in fh:
            b, archs, _size, path = line.rstrip("\n").split("\t", 3)
            if b == "dyld-cache":
                continue
            try:
                r = subprocess.run(["lipo", "-archs", os.path.join(root, path)],
                                   capture_output=True, text=True)
            except FileNotFoundError:
                if len(bad) < 50:
                    bad.append(f"{path}: lipo is not installed")
                n += 1
                continue
            lip = r.stdout.split()
            mine = archs.split(",")
            n += 1
            gx = sorted(a for a in lip if a in X86)
            mx = sorted(a for a in mine if a in X86)
            ga = sorted(a for a in lip if a not in X86)
            ma = sorted(a for a in mine if a not in X86)
            if gx == mx:
                x86_ok += 1
            if bool(ga) == bool(ma):
                arm_ok += 1
            if gx != mx or bool(ga) != bool(ma):
                if len(bad) < 50:
                    bad.append(f"{path}: census={archs} lipo={' '.join(lip) or r.stderr.strip()}")
            pairs[(",".join(ma), " ".join(ga))] += 1
    print(f"files checked: {n}")
    print(f"Intel slices identical: {x86_ok}/{n}")
    print(f"arm present/absent agrees: {arm_ok}/{n}")
    print("census arm labels -> lipo arm names (count):")
    for (m, g), c in pairs.most_common():
        print(f"  {c:6d}  {m or '-'}  ->  {g or '-'}")
    for e in bad:
        print("  MISMATCH " + e)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
