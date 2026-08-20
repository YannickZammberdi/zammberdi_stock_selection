#!/usr/bin/env python3
"""One-time backfill: build docs/history/scores.json from git history of stock indexes.

Walks every commit that touched docs/stocks/index.html or docs/asx/stocks/index.html,
extracts the `const data = [...]` rows, and records each (stock, report_date, score, type)
point. Merges into the existing scores.json (idempotent: dedup by name_code + report_date,
existing 'note' fields are preserved).

Usage: py scripts/backfill_scores_history.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT / "docs" / "history" / "scores.json"

DATA_MARKER = "const data = ["
INDEX_PATHS = ("docs/stocks/index.html", "docs/asx/stocks/index.html")


def code_from_filename(fname):
    base = fname.replace("_分析报告.html", "").replace("_C方案验证.html", "")
    parts = base.split("_")
    if re.fullmatch(r"\d{6}", parts[-1]):
        return parts[-1]
    for p in reversed(parts):
        if p == "ASX":
            continue
        if re.fullmatch(r"[A-Za-z]{2,5}", p):
            return p
    return parts[-1]


def code_from_row(r):
    fname = r.get("file", "")
    if fname:
        c = code_from_filename(fname)
        if c:
            return c
    code = r.get("code", "") or ""
    c = code.replace("_ASX", "").strip()
    if re.fullmatch(r"\d{6}", c):
        return c
    m = re.match(r"^([A-Za-z]{2,5})", c)
    if m:
        return m.group(1)
    name = r.get("name", "") or ""
    m = re.search(r"\(([^)]+)\)", name)
    if m and re.fullmatch(r"[A-Za-z]{2,5}", m.group(1)):
        return m.group(1)
    return c or (name.split()[0] if name else "")


def run(args):
    return subprocess.run(args, capture_output=True).stdout


def decode(b):
    return b.decode("utf-8", errors="replace")


def index_rows(commit, path):
    out = run(["git", "show", f"{commit}:{path}"])
    if not out:
        return None
    txt = decode(out)
    i = txt.find(DATA_MARKER)
    if i == -1:
        return None
    j = txt.find("];", i)
    if j == -1:
        return None
    try:
        return json.loads(txt[i + len(DATA_MARKER) - 1:j + 1])
    except Exception:
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not (ROOT / ".git").exists():
        print("必须在仓库根目录运行")
        return

    if HISTORY_FILE.exists():
        hist = json.loads(HISTORY_FILE.read_text(encoding="utf-8")).get("stocks", {})
    else:
        hist = {}

    log = decode(run(["git", "log", "--format=%h %ad", "--date=short", "--reverse",
                      "--"] + list(INDEX_PATHS))).splitlines()

    added = 0
    for line in log:
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        commit, date = parts
        for path in INDEX_PATHS:
            rows = index_rows(commit, path)
            if not rows:
                continue
            for r in rows:
                name = r.get("name", "") or ""
                key = code_from_row(r)
                if not key:
                    continue
                rd = r.get("date", "")
                sc = r.get("score", "")
                ty = r.get("type", "")
                if not rd or not isinstance(sc, int):
                    continue
                st = hist.setdefault(key, {"name": name, "code": key, "series": []})
                if any(p.get("d") == rd for p in st["series"]):
                    continue  # already present (possibly with a note from sync)
                st["series"].append({"d": rd, "s": sc, "t": ty or "", "n": ""})
                added += 1

    for st in hist.values():
        st["series"].sort(key=lambda p: p.get("d", ""))

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "updated": date, "stocks": hist}
    HISTORY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"回填完成：新增 {added} 个历史点，累计 {len(hist)} 只股票 -> {HISTORY_FILE}")
    for key in sorted(hist):
        pts = hist[key]["series"]
        trail = " -> ".join(f'{p["d"]} {p["s"]}({p["t"] or "?"})' for p in pts)
        print(f"  {key}: {trail}")


if __name__ == "__main__":
    main()