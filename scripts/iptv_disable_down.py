#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
import requests


def parse_entries(lines: List[str]) -> List[Tuple[int, int, str, str]]:
    out = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            ext = lines[i]
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines) and lines[j].strip().startswith("http"):
                out.append((i, j, ext, lines[j].strip()))
            i = j
        i += 1
    return out


def is_up(url: str, timeout: int = 8) -> (bool, str):
    h = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, timeout=timeout, headers=h, allow_redirects=True)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        body = r.text[:1000]
        if "#EXTM3U" in body or "#EXT-X-" in body:
            return True, "ok"
        c = (r.headers.get("content-type") or "").lower()
        if "mpegurl" in c:
            return True, "ok(ctype)"
        return False, "not-m3u"
    except Exception as e:
        return False, type(e).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", default="lista.m3u")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    p = Path(args.playlist)
    root = p.parent
    disabled_dir = root / "disabled"
    reports_dir = root / "reports"
    backups_dir = root / "backups"
    for d in [disabled_dir, reports_dir, backups_dir]:
        d.mkdir(parents=True, exist_ok=True)

    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    entries = parse_entries(lines)

    up_entries = []
    down_entries = []
    report = []

    for _, _, ext, url in entries:
        ok, reason = is_up(url)
        name = ext.split(",", 1)[1].strip() if "," in ext else ext
        report.append((name, ok, reason, url))
        if ok:
            up_entries.append((ext, url))
        else:
            down_entries.append((ext, url))

    print(f"total: {len(entries)} | up: {len(up_entries)} | down: {len(down_entries)}")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    rep = reports_dir / "down_report.txt"
    rep.write_text("\n".join([f"{ 'UP' if ok else 'DOWN' } | {name} | {reason} | {url}" for name, ok, reason, url in report]) + "\n", encoding="utf-8")

    if args.apply:
        backup = backups_dir / f"lista.pre-disable.{ts}.m3u"
        backup.write_text("\n".join(lines) + "\n", encoding="utf-8")

        active = ["#EXTM3U"]
        for ext, url in up_entries:
            active.append(ext)
            active.append(url)
        p.write_text("\n".join(active) + "\n", encoding="utf-8")

        downfile = disabled_dir / "down_channels.m3u"
        down = ["#EXTM3U"]
        for ext, url in down_entries:
            down.append(ext)
            down.append(url)
        downfile.write_text("\n".join(down) + "\n", encoding="utf-8")

        print(f"active written: {p}")
        print(f"down written: {downfile}")
        print(f"backup: {backup}")


if __name__ == "__main__":
    main()
