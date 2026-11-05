#!/usr/bin/env python3
"""Combine the per-job census files into one report.

Usage: aggregate.py INDIR OUTDIR
Writes SUMMARY.md, kexts.tsv, x86-files.tsv, arm-only.tsv, dyld-caches.tsv.
"""
import collections
import glob
import gzip
import os
import re
import sys

X86 = ("x86_64", "x86_64h", "i386")
BUCKETS = ("universal", "x86-only", "arm-only", "other", "dyld-cache")

# Intel-Mac pieces worth naming one by one. Each entry: label, regex on the
# kext bundle name.
WATCH = [
    ("AMD / Radeon GPU drivers", r"^(AMD|ATI)"),
    ("Intel GPU drivers", r"^AppleIntel.*(Graphics|Framebuffer)"),
    ("Graphics stack", r"^(IOGraphicsFamily|IONDRVSupport|IOAcceleratorFamily2?|AppleGraphicsControl|AppleGraphicsPowerManagement|AppleGPUWrangler)"),
    ("ACPI platform", r"^(AppleACPIPlatform|AppleACPI)"),
    ("Intel CPU power management", r"^(AppleIntelCPUPowerManagement|X86PlatformPlugin|ACPI_SMC_PlatformPlugin|AppleIntelSlowAdaptiveClocking)"),
    ("SMC", r"^AppleSMC"),
    ("T2 bridge", r"^(AppleBridge|BridgeAudio|AppleSSE|AppleKeyStore|AppleT2)"),
    ("Intel chipset / misc", r"^(AppleIntel|AppleHPET|AppleRTC|AppleEFI|AppleSMBus|AppleLPC|AppleUpstreamUserClient)"),
]


def load_rows(indir):
    rows = []
    for p in sorted(glob.glob(os.path.join(indir, "**", "*.tsv"), recursive=True)):
        origin = os.path.basename(p)[:-4]
        if not re.match(r"^(payload\.\d{3}|cryptex-[\w.-]+)$", origin):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t", 3)
                if len(parts) == 4:
                    b, archs, size, path = parts
                    rows.append((origin, b, archs.split(","), int(size), path))
    return rows


def group_of(origin):
    return "system payload" if origin.startswith("payload.") else origin


def kext_bundles_from_listings(indir):
    """Every .kext bundle with an Info.plist, from the find -ls listings.

    Info.plist sits at Contents/Info.plist in a normal bundle and at the
    bundle root in codeless ones (IOGraphicsFamily, the KPI pseudokexts).
    Names contain spaces, so the path is not a single whitespace token.
    """
    bundles = set()
    rx = re.compile(r"(\./.*\.kext)/(?:Contents/)?Info\.plist$")
    for p in glob.glob(os.path.join(indir, "**", "payload.*-files.txt.gz"), recursive=True):
        with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = rx.search(line.rstrip("\n"))
                if m:
                    bundles.add(m.group(1).removeprefix("./"))
    return bundles


def primary_cache(path):
    """True for dyld_shared_cache_<arch>, false for .01 / .symbols / .dylddata pieces."""
    return re.match(r"^dyld_shared_cache_[A-Za-z0-9_]+$", os.path.basename(path)) is not None


def mb(n):
    v = n / 1e6
    return f"{v:.1f}" if v < 10 else f"{v:.0f}"


def boot_program_lists():
    """(label, path-without-leading-slash) from the borrow lists, if present."""
    here = os.path.dirname(os.path.abspath(__file__))
    found = []
    for label, rel in (("startup", os.path.join("boot", "programs-stage1.txt")),
                       ("desktop and launchd", os.path.join("boot", "stage2", "programs-stage2.txt"))):
        p = os.path.join(here, rel)
        if not os.path.isfile(p):
            continue
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                found.append((label, line.lstrip("/")))
    return found


def main():
    indir, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    rows = load_rows(indir)
    md = ["# Golden Fleece census: macOS 27.2 (26B123)", ""]

    host = glob.glob(os.path.join(indir, "**", "host.txt"), recursive=True)
    if host:
        md += ["## Host (proves the decode ran on macOS 27)", "", "```"]
        md += open(host[0], encoding="utf-8", errors="replace").read().strip().splitlines()
        md += ["```", ""]

    # Totals per source
    tot = collections.defaultdict(collections.Counter)
    for origin, b, archs, size, path in rows:
        tot[group_of(origin)][b] += 1
    md += ["## Mach-O files by source", "",
           "| Source | " + " | ".join(BUCKETS) + " | total |",
           "|---" * (len(BUCKETS) + 2) + "|"]
    for g in sorted(tot):
        c = tot[g]
        md.append(f"| {g} | " + " | ".join(str(c[b]) for b in BUCKETS)
                  + f" | {sum(c.values())} |")
    md += ["", "universal = file has both arm and Intel slices. "
           "x86-only = Intel slices only.", ""]

    # dyld caches
    caches = [r for r in rows if r[1] == "dyld-cache"]
    with open(os.path.join(outdir, "dyld-caches.tsv"), "w") as fo:
        for origin, b, archs, size, path in caches:
            kind = "primary" if primary_cache(path) else "subfile"
            fo.write(f"{origin}\t{archs[0]}\t{size}\t{kind}\t{path}\n")
    if caches:
        primary = [r for r in caches if primary_cache(r[4])]
        sub = [r for r in caches if not primary_cache(r[4])]
        md += ["## dyld shared caches", "",
               "Each cache is one primary file plus its subfiles "
               "(`.01`, `.dylddata`, `.dyldlinkedit`, `.symbols`). "
               "The subfiles are pieces of that cache, not more caches.", "",
               "| Source | Arch | Primary (MB) | Subfiles | Subfiles (MB) | Path |",
               "|---|---|---|---|---|---|"]
        claimed = set()
        for origin, b, archs, size, path in sorted(primary, key=lambda r: (r[0], r[4])):
            mine = [r for r in sub if r[0] == origin and r[4].startswith(path + ".")]
            claimed.update(id(r) for r in mine)
            md.append(f"| {origin} | {archs[0]} | {mb(size)} | {len(mine)} | "
                      f"{mb(sum(r[3] for r in mine))} | {path} |")
        leftover = [r for r in sub if id(r) not in claimed]
        if leftover:
            md.append("")
            md.append(f"{len(leftover)} cache pieces did not match a primary file and are only in dyld-caches.tsv.")
        md.append("")
    counts = glob.glob(os.path.join(indir, "**", "*-dyld-images.txt"), recursive=True)
    if counts:
        md += ["### Images per main cache", "", "| Cache | Images |", "|---|---|"]
        for p in sorted(counts):
            n = sum(1 for l in open(p, errors="replace") if re.match(r"\s*\d+: ", l))
            md.append(f"| {os.path.basename(p)[:-len('-dyld-images.txt')]} | {n} |")
        md.append("")

    # Intel-bearing files by area (system payload)
    area = collections.Counter()
    with open(os.path.join(outdir, "x86-files.tsv"), "w") as fo:
        for origin, b, archs, size, path in rows:
            if b in ("universal", "x86-only") or (b == "dyld-cache" and archs[0] in X86):
                fo.write(f"{origin}\t{b}\t{','.join(archs)}\t{size}\t{path}\n")
                if group_of(origin) == "system payload":
                    area["/".join(path.split("/")[:-1][:3]) or "/"] += 1
    if area:
        md += ["## Where the Intel code sits in the system payload (top 40)", "",
               "| Area | Files with Intel slices |", "|---|---|"]
        for a, n in area.most_common(40):
            md.append(f"| {a} | {n} |")
        md.append("")

    arm_only = [r for r in rows if r[1] == "arm-only"]
    with open(os.path.join(outdir, "arm-only.tsv"), "w") as fo:
        for origin, b, archs, size, path in arm_only:
            fo.write(f"{origin}\t{','.join(archs)}\t{size}\t{path}\n")
    progs = boot_program_lists()
    if progs:
        by_path = collections.defaultdict(list)
        for origin, b, archs, size, path in rows:
            if origin.startswith("payload."):
                by_path[path].append(b)
        ok, absent, other = [], [], []
        for label, rel in progs:
            hits = by_path.get(rel)
            if not hits:
                absent.append((label, rel))
            elif set(hits) <= {"arm-only"}:
                ok.append((label, rel))
            else:
                other.append((label, rel, ",".join(sorted(set(hits)))))
        md += ["## Programs borrowed from Tahoe for Intel boot", "",
               f"The startup list and the desktop/launchd list name {len(progs)} programs "
               "that 27.2 does not ship as Intel binaries. Checked against this census:", ""]
        md.append(f"- arm-only in the system payload: {len(ok)}")
        md.append(f"- not in the system payload at all: {len(absent)}")
        md.append(f"- already has an Intel slice (the borrow list is stale): {len(other)}")
        if other:
            md.append("")
            for label, rel, buckets in other:
                md.append(f"- `{rel}` ({label}): {buckets}")
        if absent:
            md.append("")
            for label, rel in absent[:30]:
                md.append(f"- missing `{rel}` ({label})")
            if len(absent) > 30:
                md.append(f"- … {len(absent) - 30} more")
        md.append("")

    # Kexts. On this release the driver code is not inside the bundles; a
    # bundle's Contents/MacOS, when present, is listed file by file.
    kx = {}
    for origin, b, archs, size, path in rows:
        if group_of(origin) != "system payload":
            continue
        m = re.match(r"(.*\.kext)/Contents/MacOS/([^/]+)$", path)
        if m:
            kx.setdefault(m.group(1), []).append((m.group(2), archs))
    for bnd in kext_bundles_from_listings(indir):
        kx.setdefault(bnd, [])

    def desc(files):
        if not files:
            return "no executable in bundle"
        return "; ".join(f"{n} ({','.join(a)})" for n, a in sorted(files))

    with_code = sum(1 for k in kx if kx[k])
    with open(os.path.join(outdir, "kexts.tsv"), "w") as fo:
        for k in sorted(kx):
            fo.write(f"{desc(kx[k])}\t{k}\n")
    md += ["## Kernel extensions in the system payload", "",
           f"- Bundles: {len(kx)}",
           f"- Bundles with any Mach-O under Contents/MacOS: {with_code}",
           f"- Bundles with no executable inside: {len(kx) - with_code}", ""]
    for k in sorted(kx):
        if kx[k]:
            md.append(f"  - {os.path.basename(k)}: {desc(kx[k])}")
    md += ["", "## Intel-Mac drivers, one by one", ""]
    names = {k: os.path.basename(k) for k in kx}
    for label, rx in WATCH:
        hits = sorted(k for k in kx if re.search(rx, names[k]))
        md.append(f"**{label}**" + ("" if hits else ": none found"))
        for k in hits:
            md.append(f"- {names[k]}: {desc(kx[k])}  `{k}`")
        md.append("")

    with open(os.path.join(outdir, "SUMMARY.md"), "w") as fo:
        fo.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
