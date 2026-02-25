#!/usr/bin/env python3
"""Pin popular AR channels at the top while preserving relative order for the rest.

- Does NOT remove any channels.
- Keeps a stable order for non-prioritized entries.
- Matching is name-based (EXTINF display name), accent-insensitive.
"""

import argparse
import re
import unicodedata
from pathlib import Path
from typing import List, Tuple


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


def display_name(extinf: str) -> str:
    return extinf.split(",", 1)[1].strip() if "," in extinf else extinf


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Ordered by preference (top -> bottom). Aliases supported.
# Keep aliases strict to avoid accidental matches (e.g. "tn" inside "rtn").
PRIORITY_GROUPS = [
    ["c5n"],
    ["tn", "todo noticias"],
    ["cronica tv", "crónica tv"],
    ["a24"],
    ["america tv", "américa tv"],
    ["telefe"],
    ["el trece", "eltrece"],
    ["tv publica", "tv pública", "television publica"],
    ["ln+", "ln plus", "la nacion mas", "la nación más"],
    ["canal 26"],
    ["net tv", "nettv"],
    ["ciudad magazine"],
    ["tyc sports"],
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", default="lista.m3u")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    p = Path(args.playlist)
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise SystemExit("Playlist invalida")

    entries = parse_entries(lines)
    used = [False] * len(entries)

    prioritized: List[Tuple[str, str]] = []

    for aliases in PRIORITY_GROUPS:
        aliases_n = [norm(a) for a in aliases]
        for idx, (ext, url) in enumerate(entries):
            if used[idx]:
                continue
            name_n = norm(display_name(ext))
            padded = f" {name_n} "
            if any(f" {alias} " in padded for alias in aliases_n):
                prioritized.append((ext, url))
                used[idx] = True

    remaining = [entry for idx, entry in enumerate(entries) if not used[idx]]
    final_entries = prioritized + remaining

    print(f"total entries: {len(entries)}")
    print(f"prioritized moved to top: {len(prioritized)}")

    if args.apply:
        out = ["#EXTM3U"]
        for ext, url in final_entries:
            out.append(ext)
            out.append(url)
        p.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"playlist updated: {p}")


if __name__ == "__main__":
    main()
