#!/usr/bin/env python3
"""Read members of a remote ZIP with HTTP Range requests, so only the
bytes we need leave Apple's CDN.

Usage:
  remotezip.py URL --list            print size, method, offset, name
  remotezip.py URL OUTDIR MEMBER...  save members (CRC-32 checked)
"""
import io
import os
import sys
import time
import urllib.request
import zipfile

CHUNK = 64 * 1024 * 1024


class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        self.pos = 0
        self.buf_start = 0
        self.buf = b""
        self.size = int(self._get(0, 0, want_total=True))

    def _get(self, start, end, want_total=False):
        for attempt in range(8):
            try:
                req = urllib.request.Request(
                    self.url, headers={"Range": f"bytes={start}-{end}"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    if r.status != 206:
                        raise IOError(f"HTTP {r.status}, expected 206")
                    if want_total:
                        return r.headers["Content-Range"].split("/")[1]
                    data = r.read()
                if len(data) != end - start + 1:
                    raise IOError(f"short read {len(data)}")
                return data
            except Exception as e:  # retry network errors
                print(f"range {start}-{end} try {attempt + 1}: {e}",
                      file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        raise IOError(f"range {start}-{end} failed")

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        if whence == 0:
            self.pos = off
        elif whence == 1:
            self.pos += off
        else:
            self.pos = self.size + off
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        end_buf = self.buf_start + len(self.buf)
        if not (self.buf_start <= self.pos and self.pos + n <= end_buf):
            end = min(self.size, self.pos + max(n, CHUNK)) - 1
            self.buf = self._get(self.pos, end)
            self.buf_start = self.pos
        off = self.pos - self.buf_start
        out = self.buf[off:off + n]
        self.pos += len(out)
        return out

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    z = zipfile.ZipFile(HTTPRangeFile(sys.argv[1]))
    if sys.argv[2] == "--list":
        for i in z.infolist():
            print(i.file_size, i.compress_type, i.header_offset, i.filename)
        return
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    for name in sys.argv[3:]:
        info = z.getinfo(name)
        dest = os.path.join(outdir, os.path.basename(name))
        t = time.time()
        done = 0
        with z.open(info) as src, open(dest, "wb") as dst:
            while True:
                b = src.read(16 * 1024 * 1024)
                if not b:
                    break
                dst.write(b)
                done += len(b)
        if done != info.file_size:
            sys.exit(f"{name}: got {done}, expected {info.file_size}")
        secs = max(time.time() - t, 0.001)
        print(f"{name}: {done} bytes, CRC-32 ok, {done / secs / 1e6:.0f} MB/s")


if __name__ == "__main__":
    main()
