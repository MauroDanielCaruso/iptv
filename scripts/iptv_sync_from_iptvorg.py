#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
from typing import List, Tuple, Dict
import requests

REMOTE = "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/ar.m3u"


def parse_entries(lines: List[str]) -> List[Tuple[str, str]]:
    out = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            ext = lines[i]
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines) and lines[j].strip().startswith("http"):
                out.append((ext, lines[j].strip()))
            i = j
        i += 1
    return out


def name_from_extinf(ext: str) -> str:
    return ext.split(",", 1)[1].strip() if "," in ext else ""


def norm(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", default="lista.m3u")
    ap.add_argument("--remote", default=REMOTE)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    p = Path(args.playlist)
    local_lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not local_lines or not local_lines[0].startswith("#EXTM3U"):
        raise SystemExit("Playlist inválida")

    r = requests.get(args.remote, timeout=25)
    r.raise_for_status()
    remote_lines = r.text.splitlines()

    local_entries = parse_entries(local_lines)
    remote_entries = parse_entries(remote_lines)

    remote_by_name: Dict[str, Tuple[str, str]] = {}
    for ext, url in remote_entries:
        n = norm(name_from_extinf(ext))
        if n and n not in remote_by_name:
            remote_by_name[n] = (ext, url)

    # map local indices by name
    local_idx = {}
    i = 0
    while i < len(local_lines):
        if local_lines[i].startswith("#EXTINF"):
            n = norm(name_from_extinf(local_lines[i]))
            j = i + 1
            while j < len(local_lines) and (not local_lines[j].strip() or local_lines[j].strip().startswith("#")):
                j += 1
            if n and j < len(local_lines) and local_lines[j].strip().startswith("http"):
                local_idx[n] = (i, j)
            i = j
        i += 1

    updates = 0
    adds = 0

    for n, (rext, rurl) in remote_by_name.items():
        if n in local_idx:
            ei, ui = local_idx[n]
            if local_lines[ui].strip() != rurl:
                local_lines[ui] = rurl
                updates += 1
        else:
            local_lines.append(rext)
            local_lines.append(rurl)
            adds += 1

    print(f"remote entries: {len(remote_by_name)}")
    print(f"updated URLs: {updates}")
    print(f"added channels: {adds}")

    if args.apply and (updates or adds):
        p.write_text("\n".join(local_lines) + "\n", encoding="utf-8")
        print("playlist updated")


if __name__ == "__main__":
    main()
