#!/usr/bin/env python3
"""Sync stock-learning/stocks-analysis reports to docs/ (GitHub Pages).

Replaces the gh-pages-sync skill: copies reports, prunes stale files,
regenerates all index.html data arrays, and updates home page counts.

Rules mirror stock-learning/stocks-analysis layout:
    A股/**/*.html            -> docs/stocks/        (flattened)
    ASX/**/*.html            -> docs/asx/stocks/    (flattened)
    宏观报告/*.html           -> docs/macro/
    行业报告/A股——*.html       -> docs/industry/
    行业报告/ASX——*.html       -> docs/asx/industry/
    *_交易计划.html (root/交易计划/) -> docs/plans/ or docs/asx/plans/
    验证/*_C方案验证.html        -> docs/verify/ or docs/asx/verify/  (market by code)
"""

import datetime
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "stock-learning" / "stocks-analysis"
DOCS = ROOT / "docs"

HISTORY_DIR = DOCS / "history"
HISTORY_FILE = HISTORY_DIR / "scores.json"
HISTORY_MARKER = "<!-- HISTORY-TABLE -->"

STOCK_TARGETS = [("A股", DOCS / "stocks"), ("ASX", DOCS / "asx" / "stocks")]
INDUSTRY_TARGETS = [("A股", DOCS / "industry"), ("ASX", DOCS / "asx" / "industry")]

DATA_MARKER = "const data = ["
EMPTY_ASX_PLANS = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ASX交易计划 – 股票研究笔记</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;background:#f8f9fa;color:#333}
  .wrap{max-width:800px;margin:0 auto;padding:32px 16px}
  .top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:20px;flex-wrap:wrap;gap:8px}
  .top h1{font-size:22px;font-weight:700}
  .top a{font-size:13px;color:#888;text-decoration:none}
  .top a:hover{color:#333}
  .empty{text-align:center;color:#aaa;padding:60px 20px;font-size:14px}
  .footer{text-align:center;font-size:12px;color:#ccc;margin-top:40px}
  a{color:#1a73e8;text-decoration:none}
  a:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1>📄 ASX交易计划</h1>
    <a href="../index.html">← 返回ASX首页</a>
  </div>
  <div class="empty">暂无交易计划</div>
  <div class="footer">仅限个人研究参考</div>
</div>
</body>
</html>
"""


def log(msg):
    print(msg)


# ---------------------------------------------------------------- collect sources

def collect_sources():
    """Return dict: category -> list of (rel_source, basename, market_or_type)."""
    sources = {
        "stocks": [],      # (Path, basename, market)
        "industry": [],    # (Path, basename, market)
        "macro": [],       # (Path, basename, market)
        "plans": [],       # (Path, basename, market, code)
        "verify": [],      # (Path, basename, market, code)
    }

    for market, sub in (("A股", "A股"), ("ASX", "ASX")):
        for f in (SRC / sub).rglob("*.html"):
            sources["stocks"].append((f, f.name, market))

    for f in (SRC / "行业报告").glob("*.html"):
        name = f.name
        if name.startswith("A股——"):
            market = "A股"
        elif name.startswith("ASX——"):
            market = "ASX"
        else:
            log(f"[skip] 行业报告文件名无法识别市场: {name}")
            continue
        sources["industry"].append((f, name, market))

    for f in (SRC / "宏观报告").glob("*.html"):
        m = re.match(r"(A股|ASX)_宏观环境报告_(\d{4}-\d{2}-\d{2})\.html", f.name)
        market = m.group(1) if m else "unknown"
        sources["macro"].append((f, f.name, market))

    # trade plans: root and 交易计划/ subdir
    plan_files = list((SRC / "交易计划").glob("*_交易计划.html"))
    plan_files += list(SRC.glob("*_交易计划.html"))
    for f in plan_files:
        market, code = judge_plan_market_code(f)
        sources["plans"].append((f, f.name, market, code))

    # C方案验证: flat 验证/ dir, market judged by code
    for f in (SRC / "验证").glob("*_C方案验证.html"):
        market, code = judge_verify_market_code(f)
        sources["verify"].append((f, f.name, market, code))

    return sources


def judge_plan_market_code(path):
    """Determine market (A股/ASX) and code for a trade plan file."""
    m = re.match(r".*_([^_]+)_交易计划\.html$", path.name)
    code = m.group(1) if m else ""
    if re.fullmatch(r"\d{6}", code):
        return "A股", code
    if re.search(r"[A-Za-z]", code):
        return "ASX", code
    # fallback: index.md table
    idx = SRC / "index.md"
    if idx.exists():
        for line in idx.read_text(encoding="utf-8").splitlines():
            if f"| {code} |" in line:
                if "ASX" in path.parent.name or "/ASX" in line:
                    return "ASX", code
                return "A股", code
    return "A股", code


def judge_verify_market_code(path):
    """Determine market (A股/ASX) and code for a C方案验证 file."""
    m = re.match(r".*_([^_]+)_C方案验证\.html$", path.name)
    code = m.group(1) if m else ""
    if re.fullmatch(r"\d{6}", code):
        return "A股", code
    if re.search(r"[A-Za-z]", code):
        return "ASX", code
    return "A股", code


# ---------------------------------------------------------------- copy + prune

def copy_files():
    sources = collect_sources()
    copied, skipped = 0, 0

    def do_copy(src_path, dst_dir):
        nonlocal copied, skipped
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src_path.name
        if dst.exists() and dst.read_bytes() == src_path.read_bytes():
            skipped += 1
            return
        shutil.copy2(src_path, dst)
        copied += 1
        log(f"[copy] {src_path.name} -> {dst_dir.name}/")

    for f, _, market in sources["stocks"]:
        do_copy(f, STOCK_TARGETS[0][1] if market == "A股" else STOCK_TARGETS[1][1])
    for f, _, market in sources["industry"]:
        do_copy(f, INDUSTRY_TARGETS[0][1] if market == "A股" else INDUSTRY_TARGETS[1][1])
    for f, _, _ in sources["macro"]:
        do_copy(f, DOCS / "macro")
    for f, _, market, _ in sources["plans"]:
        do_copy(f, DOCS / "plans" if market == "A股" else DOCS / "asx" / "plans")
    for f, _, market, _ in sources["verify"]:
        do_copy(f, DOCS / "verify" if market == "A股" else DOCS / "asx" / "verify")

    prune_stale(sources)
    return copied, skipped


def prune_stale(sources):
    """Delete report .html in docs/ that have no corresponding source file."""
    stock_a = {s[1] for s in sources["stocks"] if s[2] == "A股"}
    stock_asx = {s[1] for s in sources["stocks"] if s[2] == "ASX"}
    ind_a = {s[1] for s in sources["industry"] if s[2] == "A股"}
    ind_asx = {s[1] for s in sources["industry"] if s[2] == "ASX"}
    macro = {s[1] for s in sources["macro"]}
    plan_a = {s[1] for s in sources["plans"] if s[2] == "A股"}
    plan_asx = {s[1] for s in sources["plans"] if s[2] == "ASX"}
    verify_a = {s[1] for s in sources["verify"] if s[2] == "A股"}
    verify_asx = {s[1] for s in sources["verify"] if s[2] == "ASX"}

    rules = [
        (DOCS / "stocks", stock_a),
        (DOCS / "asx" / "stocks", stock_asx),
        (DOCS / "industry", ind_a),
        (DOCS / "asx" / "industry", ind_asx),
        (DOCS / "macro", macro),
        (DOCS / "plans", plan_a),
        (DOCS / "asx" / "plans", plan_asx),
        (DOCS / "verify", verify_a),
        (DOCS / "asx" / "verify", verify_asx),
    ]
    for d, keep in rules:
        if not d.exists():
            continue
        for f in d.glob("*.html"):
            if f.name == "index.html":
                continue
            if f.name not in keep:
                f.unlink()
                log(f"[prune] {f.relative_to(ROOT)}")


# ---------------------------------------------------------------- parsing helpers

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
SCORE_RE = re.compile(r"总分.{0,160}?(\d+)/100", re.S)
SCORE_RE2 = re.compile(r'<span class="score">(\d+)</span>')
SCORE_RE3 = re.compile(r"(\d+)/100")
TITLE_STOCK_RE = re.compile(r"^\s*(.*?)[(（]([^)）:：]*)[)）]")


def read_utf8(path):
    return path.read_text(encoding="utf-8", errors="replace")


def parse_date(html):
    m = DATE_RE.search(html)
    return m.group(1) if m else ""


def parse_score(html):
    for pat in (SCORE_RE, SCORE_RE2, SCORE_RE3):
        m = pat.search(html)
        if m:
            return int(m.group(1))
    return 0


def parse_stock_name_code(html, filename):
    """Returns (name, code) from title, fallback filename."""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if m:
        t = TITLE_STOCK_RE.match(m.group(1).strip())
        if t:
            return t.group(1).strip(), t.group(2).strip()
    base = re.sub(r"(_ASX)?_分析报告\.html$", "", filename)
    parts = base.split("_")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return base, ""


def code_key(filename):
    """Canonical stock identity from filename: A股 6-digit code, ASX ticker.

    Stable across time even when title/name parsing changed. Examples:
        新和成_002001_分析报告.html -> 002001
        BHP_BHP_ASX_分析报告.html   -> BHP
        Pro Medicus_PME_分析报告.html -> PME
        IAG_ASX_分析报告.html       -> IAG
    """
    base = re.sub(r"_分析报告\.html$", "", filename)
    parts = base.split("_")
    if re.fullmatch(r"\d{6}", parts[-1]):
        return parts[-1]
    for p in reversed(parts):
        if p == "ASX":
            continue
        if re.fullmatch(r"[A-Za-z]{2,5}", p):
            return p
    return parts[-1]


def normalize_type(dirname):
    return "防御性" if dirname == "防御型" else dirname


def parse_plan(html, filename):
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    name, code = "", ""
    if m:
        pm = re.search(r"^\s*(.*?)[(（]([^)）]*)[)）]\s*交易计划", m.group(1))
        if pm:
            name, code = pm.group(1).strip(), pm.group(2).strip()
    if not name or not code:
        base = re.sub(r"_交易计划\.html$", "", filename)
        parts = base.split("_")
        if len(parts) >= 2:
            name, code = parts[0], parts[1]
    date = parse_date(html)
    sm = re.search(r"状态：\s*<span class=\"tag[^\"]*\">([^<]+)</span>", html)
    status = sm.group(1).strip() if sm else "计划中"
    return {"name": name, "code": code, "date": date, "status": status}


def parse_verify_name_code(html, filename):
    """Returns (name, code) from title '药明康德(603259) C方案验证', fallback filename."""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if m:
        t = re.search(r"^\s*(.*?)[(（]([^)）:：]*)[)）]\s*C方案验证", m.group(1).strip())
        if t:
            return t.group(1).strip(), t.group(2).strip()
    base = re.sub(r"_C方案验证\.html$", "", filename)
    parts = base.split("_")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return base, ""


def parse_verify_score(html):
    """10-point score, e.g. 总评分 9/10.

    Must anchor to the 总评分 label: reports may contain other "X/10" text
    (e.g. 社保基金组合编号 502/110/107) that would false-match a bare regex.
    """
    for pat in (
        r"总评分\s*(\d+)/10",
        r"verdict-score[^>]*>\s*总评分\s*(\d+)/10",
        r"总分</t[dh]>\s*<t[dh]>\s*(\d+)/10",
        r"verdict-ok|verdict-caution|verdict-bad[^>]*>\s*(\d+)/10",
    ):
        m = re.search(pat, html)
        if m:
            return int(m.group(1))
    return 0


def parse_verify_verdict(html):
    """Map verdict class to display label."""
    m = re.search(r"verdict-(ok|caution|bad)", html)
    if not m:
        return ""
    return {"ok": "言行一致", "caution": "部分存疑", "bad": "言行不一致"}[m.group(1)]


def parse_verify_date(html):
    """验证日期：YYYY-MM-DD (meta line); fallback to first date."""
    m = re.search(r"验证日期[:：]\s*(\d{4}-\d{2}-\d{2})", html)
    return m.group(1) if m else parse_date(html)


def parse_industry_name(filename):
    m = re.match(r"(?:A股|ASX)————?([^—]+)——行业分析报告\.html", filename)
    return m.group(1).strip() if m else re.sub(r"——行业分析报告\.html$", "", filename)


def parse_macro_verdict(html):
    m = re.search(r'<div class="verdict[^"]*">\s*([^<]+?)\s*</div>', html)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- index data helpers

def read_data_array(path):
    """Return list of dict rows from an index.html `const data = [...]` block."""
    if not path.exists():
        return []
    html = read_utf8(path)
    start = html.find(DATA_MARKER)
    if start == -1:
        return []
    end = html.find("];", start)
    if end == -1:
        return []
    try:
        rows = json.loads(html[start + len(DATA_MARKER) - 1:end + 1])
        return rows if isinstance(rows, list) else []
    except json.JSONDecodeError:
        return []


def replace_data_array(path, rows):
    """Replace the `const data = [...]` block in index.html."""
    html = read_utf8(path)
    start = html.find(DATA_MARKER)
    if start == -1:
        log(f"[warn] 未找到 data 数组: {path}")
        return
    end = html.find("];", start)
    if end == -1:
        log(f"[warn] 未找到 data 数组结束: {path}")
        return
    new_block = DATA_MARKER + "\n" + rows + "];"
    path.write_text(html[:start] + new_block + html[end + 2:], encoding="utf-8")


def render_data(rows, fields, sort_keys):
    """Render rows as the JS `const data` array block, sorted desc by sort_keys."""
    rows = sorted(rows, key=lambda r: tuple(r.get(k, "") for k in sort_keys), reverse=True)
    lines = []
    for r in rows:
        item = {k: r.get(k, "") for k in fields}
        if "score" in item and item["score"] != "":
            item["score"] = int(item["score"])
        lines.append("  " + json.dumps(item, ensure_ascii=False))
    return ",\n".join(lines) if lines else ""


# ---------------------------------------------------------------- per-category index build

def build_stocks_index(market):
    src_sub = SRC / ("A股" if market == "A股" else "ASX")
    target = DOCS / "stocks" if market == "A股" else DOCS / "asx" / "stocks"
    rows = []
    for f in src_sub.rglob("*.html"):
        html = read_utf8(f)
        name, code = parse_stock_name_code(html, f.name)
        rows.append({
            "name": name,
            "code": code,
            "type": normalize_type(f.parent.name),
            "score": parse_score(html),
            "date": parse_date(html),
            "file": f.name,
        })
    replace_data_array(target / "index.html", render_data(rows, ["name", "code", "type", "score", "date", "file"], ["score", "name"]))
    log(f"[index] {market} stocks: {len(rows)} 份 -> {target}/index.html")


def build_industry_index(market):
    target = DOCS / "industry" if market == "A股" else DOCS / "asx" / "industry"
    old = {r.get("file"): r for r in read_data_array(target / "index.html")}
    rows = []
    for f in (SRC / "行业报告").glob("*.html"):
        if market == "A股" and not f.name.startswith("A股——"):
            continue
        if market == "ASX" and not f.name.startswith("ASX——"):
            continue
        html = read_utf8(f)
        name = parse_industry_name(f.name)
        if name == "":
            log(f"[warn] 行业名解析失败: {f.name}")
            continue
        prev = old.get(f.name, {})
        rows.append({
            "name": name,
            "type": prev.get("type", extract_industry_type(html)),
            "score": parse_score(html),
            "date": parse_date(html),
            "file": f.name,
        })
    replace_data_array(target / "index.html", render_data(rows, ["name", "type", "score", "date", "file"], ["score", "name"]))
    log(f"[index] {market} industry: {len(rows)} 份 -> {target}/index.html")


def extract_industry_type(html):
    m = re.search(r"(纯周期|混合周期|成长型|成长性|防御性|防御型|价值型)", html)
    return m.group(1) if m else ""


def build_plans_index(market):
    sources = collect_sources()
    rows = []
    for f, _, mkt, _ in sources["plans"]:
        if mkt != market:
            continue
        html = read_utf8(f)
        p = parse_plan(html, f.name)
        p["file"] = f.name
        rows.append(p)
    target = DOCS / "plans" if market == "A股" else DOCS / "asx" / "plans"
    target.mkdir(parents=True, exist_ok=True)
    idx = target / "index.html"

    if market == "ASX" and not rows:
        idx.write_text(EMPTY_ASX_PLANS, encoding="utf-8")
        log("[index] ASX plans: 0 份 -> 静态空页面")
        return

    if market == "ASX" and not idx.exists():
        # build full version from the A股 template
        tmpl = read_utf8(DOCS / "plans" / "index.html")
        tmpl = re.sub(r"<title>.*?</title>", "<title>ASX交易计划 – 股票研究笔记</title>", tmpl, count=1)
        tmpl = tmpl.replace("<h1>📄 交易计划</h1>", "<h1>📄 ASX交易计划</h1>")
        tmpl = tmpl.replace('href="../index.html">← 返回首页</a>', 'href="../index.html">← 返回ASX首页</a>')
        idx.write_text(tmpl, encoding="utf-8")

    replace_data_array(idx, render_data(rows, ["name", "code", "date", "status", "file"], ["date", "name"]))
    log(f"[index] {market} plans: {len(rows)} 份 -> {idx}")


def build_verify_index(market):
    target = DOCS / "verify" if market == "A股" else DOCS / "asx" / "verify"
    target.mkdir(parents=True, exist_ok=True)
    idx = target / "index.html"
    if not idx.exists():
        log(f"[warn] 缺少 index 模板: {idx}（请先手动创建）")
        return
    rows = []
    for f, _, mkt, _ in collect_sources()["verify"]:
        if mkt != market:
            continue
        html = read_utf8(f)
        name, code = parse_verify_name_code(html, f.name)
        rows.append({
            "name": name,
            "code": code,
            "verdict": parse_verify_verdict(html),
            "score": parse_verify_score(html),
            "date": parse_verify_date(html),
            "file": f.name,
        })
    replace_data_array(idx, render_data(rows, ["name", "code", "verdict", "score", "date", "file"], ["score", "name"]))
    log(f"[index] {market} verify: {len(rows)} 份 -> {idx}")


def build_macro_index():
    target = DOCS / "macro"
    target.mkdir(parents=True, exist_ok=True)
    idx = target / "index.html"
    html = read_utf8(idx)

    old = {}
    for m in re.finditer(r'href="([^"]+)"[\s\S]*?<h2>(.*?)</h2>[\s\S]*?<p>(.*?)</p>', html):
        old[m.group(1)] = m.group(3).strip()

    cards = []
    for f, name, market in sorted(collect_sources()["macro"], key=lambda x: x[2]):
        html_r = read_utf8(f)
        desc = old.get(name)
        if not desc:
            v = parse_macro_verdict(html_r)
            d = parse_date(html_r)
            desc = f"{d} · {v}" if v else d
        icon = "icon-a" if market == "A股" else "icon-asx"
        label = "A" if market == "A股" else "ASX"
        cards.append(
            f'    <a class="card" href="{name}">\n'
            f'      <div class="card-icon {icon}">{label}</div>\n'
            f'      <div class="card-body">\n'
            f'        <h2>{market} 宏观环境报告</h2>\n'
            f'        <p>{desc}</p>\n'
            f'      </div>\n'
            f'    </a>'
        )

    m = re.search(r'(<div class="grid">)[\s\S]*?(</div>\s*<div class="footer">)', html)
    if m:
        new_html = html[:m.start()] + m.group(1) + "\n" + "\n".join(cards) + "\n  " + m.group(2) + html[m.end():]
        idx.write_text(new_html, encoding="utf-8")
        log(f"[index] macro: {len(cards)} 份 -> {target}/index.html")


# ---------------------------------------------------------------- score history

def load_history():
    """Load docs/history/scores.json -> dict keyed by 'name_code'."""
    if not HISTORY_FILE.exists():
        return {}
    try:
        payload = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return payload.get("stocks", {}) if isinstance(payload, dict) else {}
    except Exception:
        log(f"[warn] scores.json 解析失败，重置为空历史")
        return {}


def save_history(hist):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "updated": datetime.date.today().isoformat(), "stocks": hist}
    HISTORY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[history] 更新 {HISTORY_FILE.relative_to(ROOT)} ({len(hist)} 只股票)")


def parse_score_note(html):
    """Extract 评分口径说明 (≤40字) from the template's .score-note element."""
    i = html.find('class="score-note"')
    if i == -1:
        return ""
    seg = html[i:i + 600]
    seg = re.sub(r"<[^>]+>", "|", seg)
    seg = re.sub(r"\|+", "|", seg)
    m = re.search(r"评分口径说明[:：]\s*\|?\s*([^|]+?)(?:\||$)", seg)
    if not m:
        return ""
    note = re.sub(r"【[^】]*】", "", m.group(1)).strip()
    note = re.sub(r"\s+", " ", note)
    if not note or "{" in note or "≤40字" in note:
        return ""
    return note[:80]


def render_history_table(hist, key):
    """Build the 评分沿革 table HTML for a stock key from history."""
    st = hist.get(key)
    if not st or not st.get("series"):
        return ""
    points = sorted(st["series"], key=lambda p: p.get("d", ""))
    rows = []
    prev_t = ""
    for p in points:
        s = p.get("s", "")
        t = p.get("t", "") or ""
        n = p.get("n", "") or ""
        if not n and t and prev_t and t != prev_t:
            n = f"换评分体系（{prev_t}→{t}）"
        prev_t = t
        if isinstance(s, int):
            cls = "good" if s >= 80 else ("neutral" if s >= 60 else "bad")
            sc = f'<td class="{cls}" style="font-weight:bold">{s}/100</td>'
        else:
            sc = f"<td>{s}</td>"
        rows.append(
            f'  <tr><td>{p.get("d", "")}</td>{sc}<td>{t}</td>'
            f'<td style="text-align:left">{n or "—"}</td></tr>'
        )
    style = (
        '<style>'
        '.history-table{width:100%;border-collapse:collapse;margin:8px 0 16px;'
        'font-size:13px}'
        '.history-table th,.history-table td{border:1px solid #ddd;padding:6px 8px;'
        'text-align:center}'
        '.history-table th{background:#f0f0f0;font-weight:bold}'
        '.history-table td.good{color:#27ae60}.history-table td.neutral{color:#e67e22}'
        '.history-table td.bad{color:#c0392b}'
        '</style>'
    )
    return (
        '<h2 style="margin-top:16px">评分沿革</h2>\n'
        + style +
        '<table class="history-table">\n'
        '  <tr><th>日期</th><th>评分</th><th>评分体系</th><th>变化原因</th></tr>\n'
        + "\n".join(rows) +
        "\n</table>"
    )


def inject_history(dst_path, hist, key):
    """Replace HISTORY_MARKER in a docs copy with the 评分沿革 table."""
    html = read_utf8(dst_path)
    if HISTORY_MARKER not in html:
        return False
    table = render_history_table(hist, key)
    new_html = html.replace(HISTORY_MARKER, table)
    if new_html != html:
        dst_path.write_text(new_html, encoding="utf-8")
        log(f"[history] 注入评分沿革 -> {dst_path.name}")
        return True
    return False


def sync_stock_history(market):
    """Upsert current stock report scores into history, inject 沿革 into docs copies."""
    src_sub = SRC / ("A股" if market == "A股" else "ASX")
    target = DOCS / "stocks" if market == "A股" else DOCS / "asx" / "stocks"
    hist = load_history()
    changed = False
    for f in sorted(src_sub.rglob("*.html")):
        html = read_utf8(f)
        key = code_key(f.name)
        name, code = parse_stock_name_code(html, f.name)
        date = parse_date(html)
        score = parse_score(html)
        type_ = normalize_type(f.parent.name)
        note = parse_score_note(html)
        if not key or not date or not score:
            continue
        st = hist.setdefault(key, {"name": name, "code": code, "series": []})
        found = False
        for p in st["series"]:
            if p.get("d") == date:
                if p.get("s") != score or p.get("t") != type_ or p.get("n") != note:
                    p["s"], p["t"], p["n"] = score, type_, note
                    changed = True
                found = True
                break
        if not found:
            st["series"].append({"d": date, "s": score, "t": type_, "n": note})
            changed = True
        dst = target / f.name
        if dst.exists():
            inject_history(dst, hist, key)
    for st in hist.values():
        st["series"].sort(key=lambda p: p.get("d", ""))
    if changed:
        save_history(hist)
    log(f"[history] {market} 股票历史同步完成（{len(hist)} 只股票入账）")


# ---------------------------------------------------------------- home page counts

def count_html_files(d):
    if not d.exists():
        return 0
    return sum(1 for f in d.glob("*.html") if f.name != "index.html")


def update_home_counts():
    macro_a = sum(1 for f in (SRC / "宏观报告").glob("A股_*.html"))
    macro_asx = sum(1 for f in (SRC / "宏观报告").glob("ASX_*.html"))
    counts_a = {
        "macro": macro_a,
        "industry": count_html_files(DOCS / "industry"),
        "stocks": count_html_files(DOCS / "stocks"),
        "plans": count_html_files(DOCS / "plans"),
        "verify": count_html_files(DOCS / "verify"),
    }
    counts_asx = {
        "macro": macro_asx,
        "industry": count_html_files(DOCS / "asx" / "industry"),
        "stocks": count_html_files(DOCS / "asx" / "stocks"),
        "plans": count_html_files(DOCS / "asx" / "plans"),
        "verify": count_html_files(DOCS / "asx" / "verify"),
    }

    def patch(path, counts):
        html = read_utf8(path)
        card_re = re.compile(r'(<a class="card" href="[^"]+"[\s\S]*?<span class="count">)([^<]*)(</span>)')

        def _repl(m):
            c = _count_for(m.group(0), counts)
            if c is None:
                return m.group(0)
            return m.group(1) + f"{c} 份" + m.group(3)

        new_html, n = card_re.subn(_repl, html)
        if new_html != html:
            path.write_text(new_html, encoding="utf-8")
            log(f"[home] 更新计数 -> {path.relative_to(ROOT)}")
        else:
            log(f"[home] 计数无变化 -> {path.relative_to(ROOT)}")

    patch(DOCS / "index.html", counts_a)
    patch(DOCS / "asx" / "index.html", counts_asx)


def _count_for(card, counts):
    m = re.search(r'href="([^"]+)"', card)
    href = m.group(1) if m else ""
    if "macro" in href:
        return counts["macro"]
    if href.endswith("industry/index.html"):
        return counts["industry"]
    if href.endswith("stocks/index.html"):
        return counts["stocks"]
    if href.endswith("plans/index.html"):
        return counts["plans"]
    if href.endswith("verify/index.html"):
        return counts["verify"]
    return None  # untouched


# ---------------------------------------------------------------- main

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    dry = "--dry-run" in sys.argv
    if dry:
        print("dry-run 模式：不写文件（本脚本当前只支持直接执行，dry-run 仅提示）")
    copied, skipped = copy_files()
    build_stocks_index("A股")
    build_stocks_index("ASX")
    sync_stock_history("A股")
    sync_stock_history("ASX")
    build_industry_index("A股")
    build_industry_index("ASX")
    build_plans_index("A股")
    build_plans_index("ASX")
    build_verify_index("A股")
    build_verify_index("ASX")
    build_macro_index()
    update_home_counts()
    log(f"完成：复制 {copied}，跳过 {skipped}（内容一致）")


if __name__ == "__main__":
    main()