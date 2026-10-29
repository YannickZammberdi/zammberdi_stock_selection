#!/usr/bin/env python3
"""Watchlist-only earnings updates. Dry-run by default; --run requires CI git push access."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATE = Path("docs/history/auto_updates.json")
TZ = ZoneInfo("Australia/Sydney")


def expected_schedule(now):
    local = now.astimezone(TZ)
    scheduled = local.replace(hour=8, minute=30, second=0, microsecond=0)
    utc = scheduled.astimezone(dt.timezone.utc)
    return f"30 {utc.hour} * * *"


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, check=True)


def calendar(stocks, today):
    # Include the previous year: a January check must still discover last year's reports.
    codes = ",".join(f'"{s["code"]}"' for s in stocks)
    query = {
        "reportName": "RPT_PUBLIC_BS_APPOIN", "columns": "ALL",
        "filter": f'(SECURITY_CODE in ({codes}))(REPORT_YEAR>="{today.year - 1}")',
        "pageSize": 500, "pageNumber": 1,
        "sortColumns": "REPORT_DATE", "sortTypes": -1,
    }
    rows = []
    while True:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get?" + urlencode(query)
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={"Referer": "https://data.eastmoney.com/"}), timeout=45) as response:
                    result = json.load(response)
                if not result.get("success") or not result.get("result"):
                    raise ValueError(f"Calendar API failed: {result.get('message')}")
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        page = result["result"]
        rows.extend(page["data"])
        if query["pageNumber"] >= page["pages"]:
            return rows
        query["pageNumber"] += 1


def report_path(stock):
    return Path("docs/stocks") / f'{stock["name"]}_{stock["code"]}_分析报告.html'


def covered_period(stock, state):
    values = [stock.get("covered_period", ""), state.get("coverage", {}).get(stock["code"], "")]
    report = ROOT / report_path(stock)
    if report.exists():
        text = report.read_text(encoding="utf-8")
        # Only explicit coverage dates count. The report's analysis date is NOT coverage.
        values.extend(re.findall(r'<!-- COVERAGE period=(\d{4}-\d{2}-\d{2}) -->', text))
        values.extend(re.findall(r'财报截至[：:]\s*(\d{4}-\d{2}-\d{2})', text))
    return max(values)


def plan(config, state, rows, today):
    latest = {}
    for row in rows:
        period = (row.get("REPORT_DATE") or "")[:10]
        published = (row.get("ACTUAL_PUBLISH_DATE") or "")[:10]
        # Never trust IS_PUBLISH alone: some API rows even carry future actual dates.
        if row.get("IS_PUBLISH") != "1" or not published or published >= today.isoformat():
            continue
        if not re.fullmatch(r"\d{4}-(03-31|06-30|09-30|12-31)", period) or period >= today.isoformat():
            continue
        code = row["SECURITY_CODE"]
        if code not in latest or period > latest[code]["period"]:
            latest[code] = {"period": period, "published": published}
    queue = []
    for stock in config["stocks"]:
        event = latest.get(stock["code"])
        if event and event["period"] > covered_period(stock, state):
            queue.append({**stock, **event})
    # Oldest uncovered disclosure first. Only the newest period per stock is generated.
    queue.sort(key=lambda s: (s["published"], s["code"]))
    used = sum(a["day"] == today.isoformat() for a in state.get("attempts", []))
    limit = max(0, min(5, int(config.get("daily_limit", 5))) - used)
    return queue[:limit]


def publish(paths, message):
    git("add", "--", *map(str, paths))
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-m", message], cwd=ROOT, check=True)
    # Handle a human pushing while generation is running; never force-push.
    for attempt in range(3):
        result = subprocess.run(["git", "push", "origin", "HEAD:master"], cwd=ROOT)
        if result.returncode == 0:
            return
        if attempt < 2:
            git("pull", "--rebase", "origin", "master")
    raise RuntimeError("Push failed; stopping instead of generating more reports")


def save_state(state):
    path = ROOT / STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record_updates(updates):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("updated=" + json.dumps(updates, ensure_ascii=True) + "\n")


def validate(text, period, old):
    if text == old:
        raise ValueError("Model did not change the report")
    for tab in ("summary", "l1", "l2", "l3", "l4", "l5", "l6"):
        if f'id="tab-{tab}"' not in text:
            raise ValueError(f"Missing tab {tab}")
    if not re.search(r"\b\d{1,3}/100\b", text) or "<!-- TRACK " not in text:
        raise ValueError("Missing score / TRACK marker")
    if f"<!-- COVERAGE period={period} -->" not in text:
        raise ValueError("Missing target earnings coverage marker")
    if "HISTORY-TABLE" not in text or "</html>" not in text.lower():
        raise ValueError("Incomplete HTML report")


def generate(stock, model):
    target = report_path(stock)
    old_path = ROOT / target
    old = old_path.read_text(encoding="utf-8") if old_path.exists() else ""
    # Isolate model edits; only the requested HTML is brought back to the real checkout.
    with tempfile.TemporaryDirectory(prefix="stock-update-") as temp:
        workspace = Path(temp) / "repo"
        git("clone", "--quiet", "--no-hardlinks", str(ROOT), str(workspace))
        prompt = (
            f'使用 stock-report-tab skill，重新生成 A股 {stock["name"]}（{stock["code"]}）财务分析报告，'
            f'只覆盖 {target.as_posix()}。必须核验并纳入截至 {stock["period"]} 的正式财报原文，'
            f'实际披露日期 {stock["published"]}；保留必要年报和中报历史对比。'
            '不得仅改日期或沿用旧数冒充更新。查不到新财报则停止，不得标记成功。'
            f'核验完成后在HTML中加入 <!-- COVERAGE period={stock["period"]} -->。'
            '保留7个Tab、总分、TRACK及HISTORY-TABLE标记。不要运行sync、git提交或修改其他文件。'
        )
        subprocess.run(["opencode", "run", "--model", model, "--auto", prompt], cwd=workspace,
                       check=True, timeout=30 * 60)
        text = (workspace / target).read_text(encoding="utf-8")
        validate(text, stock["period"], old)
        old_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.write_text(text, encoding="utf-8")


def generate_with_fallback(stock, config):
    primary = config["model"]
    try:
        generate(stock, primary)
        return primary
    except Exception as exc:
        fallback = config.get("fallback_model")
        if not fallback or fallback == primary:
            raise
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise RuntimeError("Primary failed; DEEPSEEK_API_KEY is missing for official fallback") from exc
        print(f'Primary failed ({type(exc).__name__}); retrying {stock["code"]} with {fallback}', flush=True)
        # generate() starts with a fresh clone; never reuse partial model edits.
        generate(stock, fallback)
        return fallback


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Generate and push, not just check")
    args = parser.parse_args()
    now = dt.datetime.now(TZ)
    today = now.date()
    schedule = os.environ.get("SCHEDULE_CRON")
    if schedule and schedule != expected_schedule(now):
        print("Inactive Sydney daylight-saving schedule; skipping")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write("count=0\n")
        return
    config = read_json(ROOT / "watchlist.json")
    if not config["stocks"]:
        print("Watchlist empty")
        return
    state = read_json(ROOT / STATE, {"coverage": {}, "attempts": []})
    queue = plan(config, state, calendar(config["stocks"], today), today)
    print(json.dumps(queue, ensure_ascii=False, indent=2), flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"count={len(queue)}\n")
    if not args.run:
        return
    failures = []
    updates = []
    for stock in queue:
        day = dt.datetime.now(TZ).date().isoformat()
        state = read_json(ROOT / STATE, state)
        used = sum(a["day"] == day for a in state["attempts"])
        if used >= min(5, int(config.get("daily_limit", 5))):
            break
        # Reserve budget BEFORE invoking the model. A crash or manual rerun cannot exceed 5/day.
        entry = {"day": day, "code": stock["code"], "period": stock["period"], "status": "started"}
        state["attempts"].append(entry)
        save_state(state)
        publish([STATE], f'auto-update: reserve {stock["code"]} {stock["period"]}')
        try:
            entry["model"] = generate_with_fallback(stock, config)
        except Exception as exc:
            print(f'FAILED {stock["code"]}: {exc}', flush=True)
            entry["status"] = "failed"
            save_state(state)
            publish([STATE], f'auto-update: failed {stock["code"]}')
            failures.append(stock["code"])
            continue
        state["coverage"][stock["code"]] = stock["period"]
        entry["status"] = "success"
        save_state(state)
        subprocess.run([sys.executable, "scripts/sync_ghpages.py"], cwd=ROOT, check=True)
        publish(["docs"], f'auto-update: {stock["name"]} {stock["period"]}')
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        updates.append({"name": stock["name"], "code": stock["code"],
                        "period": stock["period"], "file": report_path(stock).as_posix(), "commit": commit})
        # Emit after every successful push, so a later stock failure still permits notification.
        record_updates(updates)
        # Refresh state after a possible rebase.
        state = read_json(ROOT / STATE)
    if failures:
        raise RuntimeError(f"Failed reports (will retry on a later check): {failures}")


if __name__ == "__main__":
    main()
