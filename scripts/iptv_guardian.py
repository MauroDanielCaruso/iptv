#!/usr/bin/env python3
import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import requests


@dataclass
class Entry:
    extinf_idx: int
    url_idx: int
    extinf: str
    url: str
    name: str


def parse_entries(lines: List[str]) -> List[Entry]:
    entries: List[Entry] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            name = line.split(",", 1)[1].strip() if "," in line else ""
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines):
                url = lines[j].strip()
                if url.startswith("http"):
                    entries.append(Entry(i, j, lines[i], lines[j], name))
            i = j
        i += 1
    return entries


def is_live_m3u8(url: str, timeout: int = 12) -> (bool, str):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
    }
    try:
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        ctype = (r.headers.get("content-type") or "").lower()
        body = r.text[:1200]
        looks_m3u = ("#EXTM3U" in body) or ("#EXT-X-" in body)
        if looks_m3u:
            return True, "ok"
        if "mpegurl" in ctype or "application/vnd.apple.mpegurl" in ctype:
            return True, "ok(ctype)"
        return False, "not-m3u8-content"
    except Exception as e:
        return False, f"error:{type(e).__name__}"


def match_target(entry_name: str, aliases: List[str]) -> bool:
    s = entry_name.lower()
    for a in aliases:
        token = a.lower().strip()
        if not token:
            continue
        if len(token) <= 3:
            # avoid false positives like TN matching RTN
            if re.search(rf"\\b{re.escape(token)}\\b", s):
                return True
        else:
            if token in s:
                return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Checks key channels in M3U and replaces dead URLs with approved candidates.")
    ap.add_argument("--config", default="config.targets.json")
    ap.add_argument("--apply", action="store_true", help="Apply replacements to playlist")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    root = cfg_path.parent
    playlist_path = (root / cfg["playlist_path"]).resolve()
    backup_dir = (root / cfg.get("backup_dir", "backups")).resolve()
    report_dir = (root / cfg.get("report_dir", "reports")).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    lines = playlist_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    entries = parse_entries(lines)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "playlist": str(playlist_path),
        "changes": [],
        "channels": []
    }

    changed = False

    for target in cfg["targets"]:
        name = target["name"]
        aliases = target.get("aliases", [])
        candidates = target.get("replacement_candidates", [])

        matched = [e for e in entries if match_target(e.name, aliases)]
        ch = {
            "name": name,
            "found_entries": len(matched),
            "current": [],
            "status": "missing"
        }

        alive_entry: Optional[Entry] = None
        for e in matched:
            ok, reason = is_live_m3u8(e.url.strip())
            ch["current"].append({"name": e.name, "url": e.url.strip(), "alive": ok, "reason": reason})
            if ok and alive_entry is None:
                alive_entry = e

        if alive_entry:
            ch["status"] = "ok"
            report["channels"].append(ch)
            continue

        replacement = None
        for c in candidates:
            ok, reason = is_live_m3u8(c)
            if ok:
                replacement = c
                break

        if replacement and args.apply:
            if matched:
                old = matched[0].url.strip()
                lines[matched[0].url_idx] = replacement
                changed = True
                ch["status"] = "replaced"
                ch["replacement"] = replacement
                report["changes"].append({"channel": name, "action": "replace", "old": old, "new": replacement})
            else:
                lines.append(target["extinf_template"])
                lines.append(replacement)
                changed = True
                ch["status"] = "added"
                ch["replacement"] = replacement
                report["changes"].append({"channel": name, "action": "add", "new": replacement})
        else:
            ch["status"] = "dead-no-approved-replacement" if matched else "missing"

        report["channels"].append(ch)

    if changed and args.apply:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backup_dir / f"lista.{ts}.m3u"
        backup.write_text("\n".join(playlist_path.read_text(encoding="utf-8", errors="ignore").splitlines()) + "\n", encoding="utf-8")
        playlist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report["backup"] = str(backup)

    out_json = report_dir / "latest_report.json"
    out_txt = report_dir / "latest_report.txt"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    txt_lines = [
        f"IPTV guardian report - {report['timestamp']}",
        f"Playlist: {playlist_path}",
        ""
    ]
    for ch in report["channels"]:
        txt_lines.append(f"- {ch['name']}: {ch['status']}")
        for c in ch.get("current", []):
            txt_lines.append(f"    · {c['name']} -> {'UP' if c['alive'] else 'DOWN'} ({c['reason']})")
        if ch.get("replacement"):
            txt_lines.append(f"    · replacement: {ch['replacement']}")
    if report["changes"]:
        txt_lines.append("\nChanges:")
        for c in report["changes"]:
            txt_lines.append(f"- {c}")

    out_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_txt}")
    if changed:
        print("Playlist updated")
    else:
        print("No playlist changes")


if __name__ == "__main__":
    main()
