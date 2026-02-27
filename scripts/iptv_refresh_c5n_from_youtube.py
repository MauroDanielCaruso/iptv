#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional

DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=SF06Qy1Ct6Y"


def parse_entries(lines: List[str]) -> List[Tuple[int, int, str]]:
    entries = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            name = lines[i].split(",", 1)[1].strip() if "," in lines[i] else ""
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines) and lines[j].strip().startswith("http"):
                entries.append((i, j, name))
            i = j
        i += 1
    return entries


def get_live_url(video_url: str) -> str:
    cmd = ["yt-dlp", "-f", "b", "-g", video_url]
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip().splitlines()
    urls = [line.strip() for line in out if line.strip().startswith("http")]
    if not urls:
        raise RuntimeError("yt-dlp no devolvió URL de stream")
    return urls[-1]


def find_c5n_url_idx(lines: List[str]) -> Optional[int]:
    for _, url_i, name in parse_entries(lines):
        if name.lower() == "c5n":
            return url_i
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Actualiza la URL de C5N con una URL fresca obtenida desde YouTube (yt-dlp).")
    ap.add_argument("--playlist", default="lista.m3u")
    ap.add_argument("--video-url", default=DEFAULT_VIDEO_URL)
    ap.add_argument("--apply", action="store_true", help="Escribe cambios en la playlist")
    args = ap.parse_args()

    playlist = Path(args.playlist)
    if not playlist.exists():
        print(f"Playlist no encontrada: {playlist}", file=sys.stderr)
        return 2

    lines = playlist.read_text(encoding="utf-8", errors="ignore").splitlines()
    idx = find_c5n_url_idx(lines)
    if idx is None:
        print("No encontré entrada C5N en la playlist", file=sys.stderr)
        return 3

    old_url = lines[idx].strip()
    try:
        new_url = get_live_url(args.video_url)
    except Exception as e:
        print(f"Error obteniendo URL con yt-dlp: {e}", file=sys.stderr)
        return 4

    print(f"old: {old_url}")
    print(f"new: {new_url}")

    if old_url == new_url:
        print("Sin cambios")
        return 0

    if args.apply:
        lines[idx] = new_url
        playlist.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Playlist actualizada: {playlist}")
    else:
        print("Dry-run. Usá --apply para guardar")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
