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

# Models sometimes type the marker with full-width or non-breaking spaces; \s covers those.
COVERAGE_RE = re.compile(r"<!--\s*COVERAGE\s+period\s*=\s*(\d{4}-\d{2}-\d{2})\s*-->")
# A report may state the covered period in prose instead of the marker ("数据截止：2026 年三季报（2026-09-30…）").
PERIOD_LABEL_RE = re.compile(
    r"(?:数据截至|数据截止|财报截至|财报截止|报告期|财报期)[^<\n]{0,40}?(\d{4}-\d{2}-\d{2})")


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
        values.extend(COVERAGE_RE.findall(text))
        values.extend(re.findall(r'财报截至[：:]\s*(\d{4}-\d{2}-\d{2})', text))
    return max(values)


def latest_disclosures(rows, today):
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
    return latest


def plan(config, state, rows, today, manual=False):
    latest = latest_disclosures(rows, today)
    queue = []
    for stock in config["stocks"]:
        event = latest.get(stock["code"])
        if event and event["period"] > covered_period(stock, state):
            queue.append({**stock, **event})
    # Oldest uncovered disclosure first. Only the newest period per stock is generated.
    queue.sort(key=lambda s: (s["published"], s["code"]))
    # A manual run is user-initiated; the daily budget only throttles scheduled runs.
    used = 0 if manual else sum(
        a["day"] == today.isoformat() and a.get("status") != "paid-reservation"
        for a in state.get("attempts", []))
    limit = max(0, min(5, int(config.get("daily_limit", 5))) - used)
    return queue[:limit]


def forced_plan(config, rows, today, code):
    """Regenerate one stock on demand, ignoring the coverage record."""
    stock = next((s for s in config["stocks"] if s["code"] == code), None)
    if stock is None:
        raise SystemExit(f"{code} is not in watchlist.json")
    event = latest_disclosures(rows, today).get(code)
    if not event:
        raise SystemExit(f"No disclosed report found for {code}")
    return [{**stock, **event}]


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


def ensure_coverage(text, period):
    """Return text with exactly one canonical COVERAGE marker for period.

    Tolerates models writing the marker with odd whitespace, and injects it when the
    report body already states the same covered period.
    """
    marker = f"<!-- COVERAGE period={period} -->"
    found = COVERAGE_RE.findall(text)
    if found and set(found) == {period}:
        return COVERAGE_RE.sub(marker, text)
    if found:
        raise ValueError(f"Coverage marker {sorted(set(found))} does not match {period}")
    if period not in PERIOD_LABEL_RE.findall(text):
        raise ValueError("Missing target earnings coverage marker")
    # Append at the very end: sync_ghpages parses the first date in the file, so an extra
    # date must never precede the report's own analysis date.
    for anchor in ("</body>", "</html>"):
        index = text.rfind(anchor)
        if index != -1:
            return text[:index] + marker + "\n" + text[index:]
    return text + "\n" + marker + "\n"


def validate(text, period, old):
    if text == old:
        raise ValueError("Model did not change the report")
    for tab in ("summary", "l1", "l2", "l3", "l4", "l5", "l6"):
        if f'id="tab-{tab}"' not in text:
            raise ValueError(f"Missing tab {tab}")
    if not re.search(r"\b\d{1,3}/100\b", text) or "<!-- TRACK " not in text:
        raise ValueError("Missing score / TRACK marker")
    text = ensure_coverage(text, period)
    if "HISTORY-TABLE" not in text or "</html>" not in text.lower():
        raise ValueError("Incomplete HTML report")
    return text


def workspace_env(workspace):
    """opencode derives its project directory from $PWD, not from the process cwd."""
    return dict(os.environ, PWD=str(workspace), OLDPWD=str(ROOT))


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
            f'核验完成后在HTML中加入 <!-- COVERAGE period={stock["period"]} -->（标记内只用半角空格）。'
            '保留7个Tab、总分、TRACK及HISTORY-TABLE标记。不要运行sync、git提交或修改其他文件。'
            'HTML较大，请分段编辑（例如用python脚本写入），避免单次写入超长内容失败。'
        )
        # opencode resolves its workspace from $PWD, not from the process cwd: without this the
        # model edits ROOT instead of the throwaway clone (and the clone stays untouched).
        subprocess.run(["opencode", "run", "--model", model, "--auto", prompt], cwd=workspace,
                       env=workspace_env(workspace), check=True,
                       timeout=int(os.environ.get("MODEL_TIMEOUT_SECONDS", 600)))
        text = (workspace / target).read_text(encoding="utf-8")
        if old_path.exists() and old_path.read_text(encoding="utf-8") != old:
            # Never commit edits the model made against the wrong checkout.
            git("checkout", "--", target.as_posix())
            raise RuntimeError("Model wrote to the real checkout instead of the isolated clone")
        text = validate(text, stock["period"], old)
        old_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.write_text(text, encoding="utf-8")


def paid_fallback_used(state, day):
    return sum(1 for a in state.get("attempts", []) if a.get("day") == day and a.get("paid_fallback"))


def reserve_paid_fallback(stock, day):
    """Book the paid call on the remote before spending, so parallel jobs cannot overspend."""
    state = read_json(ROOT / STATE, {"coverage": {}, "attempts": []})
    state["attempts"].append({"day": day, "code": stock["code"], "period": stock["period"],
                              "status": "paid-reservation", "paid_fallback": True})
    save_state(state)
    publish([STATE], f'auto-update: paid fallback {stock["code"]}')


def generate_with_fallback(stock, config, allow_paid=True, reserve=None):
    """Free primary model first; the paid fallback is capped (default: once per day).

    Returns (model_used, used_paid_fallback).
    """
    primary = config["model"]
    try:
        generate(stock, primary)
        return primary, False
    except Exception as exc:
        fallback = (config.get("fallback_model") or "").strip()
        if fallback and fallback != primary and allow_paid:
            if not os.environ.get("DEEPSEEK_API_KEY"):
                raise RuntimeError("Primary failed; DEEPSEEK_API_KEY is missing for the configured fallback") from exc
            if reserve:
                reserve()
            print(f'Primary failed ({type(exc).__name__}); retrying {stock["code"]} with {fallback} (paid)', flush=True)
            # generate() starts with a fresh clone; never reuse partial model edits.
            generate(stock, fallback)
            return fallback, True
        if fallback and fallback != primary:
            print(f'Primary failed ({type(exc).__name__}); paid fallback already used today, '
                  f'retrying {stock["code"]} once with {primary}', flush=True)
        else:
            print(f'Primary failed ({type(exc).__name__}); retrying {stock["code"]} once with {primary}', flush=True)
        generate(stock, primary)
        return primary, False


def generate_one(code, outdir):
    """Generate one report in an isolated clone and hand the HTML to the publish job."""
    config = read_json(ROOT / "watchlist.json")
    stock = next((s for s in config["stocks"] if s["code"] == code), None)
    if stock is None:
        raise SystemExit(f"{code} is not in watchlist.json")
    stock = {**stock, "period": os.environ["REPORT_PERIOD"], "published": os.environ["REPORT_PUBLISHED"]}
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    result = {"code": code, "name": stock["name"], "period": stock["period"],
              "published": stock["published"], "status": "failed"}
    state = read_json(ROOT / STATE, {"coverage": {}, "attempts": []})
    day = dt.datetime.now(TZ).date().isoformat()
    limit = int(config.get("fallback_daily_limit", 1))
    allow_paid = paid_fallback_used(state, day) < limit
    if not allow_paid:
        print(f"Paid fallback already used {limit} time(s) on {day}; free model only", flush=True)
    try:
        model, paid = generate_with_fallback(
            stock, config, allow_paid, reserve=lambda: reserve_paid_fallback(stock, day))
        result["model"] = model
        result["paid_fallback"] = paid
        (out / "report.html").write_text((ROOT / report_path(stock)).read_text(encoding="utf-8"), encoding="utf-8")
        result["status"] = "success"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
        print(f'FAILED {code}: {exc}', flush=True)
        raise
    finally:
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish_results(results_dir):
    """Write validated reports and push each one immediately, then refresh Pages indexes.

    Pushing per report keeps finished work durable: if the index sync or a later push fails,
    the report and its COVERAGE marker are already on master and the next check will not
    regenerate it. Re-running the failed publish job reuses the uploaded artifacts instead.
    """
    state = read_json(ROOT / STATE, {"coverage": {}, "attempts": []})
    day = dt.datetime.now(TZ).date().isoformat()
    done, failed = [], []
    results = sorted(Path(results_dir).glob("*/result.json"))
    if not results:
        print("No results to publish")
        return
    for path in results:
        result = json.loads(path.read_text(encoding="utf-8"))
        stock = {"code": result["code"], "name": result["name"], "period": result["period"]}
        entry = {"day": day, "code": stock["code"], "period": stock["period"],
                 "status": "failed"}
        if result.get("model"):
            entry["model"] = result["model"]
        if result.get("paid_fallback"):
            entry["paid_fallback"] = True
        try:
            if result["status"] != "success":
                raise ValueError(result.get("error", "generation failed"))
            report = ROOT / report_path(stock)
            old = report.read_text(encoding="utf-8") if report.exists() else ""
            if stock["period"] in COVERAGE_RE.findall(old):
                # A previous publish already landed this report; re-running must not fail.
                print(f'{stock["code"]} already published for {stock["period"]}; skipping', flush=True)
                already = True
            else:
                text = validate((path.parent / "report.html").read_text(encoding="utf-8"), stock["period"], old)
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text(text, encoding="utf-8")
                already = False
        except Exception as exc:
            print(f'FAILED {stock["code"]}: {exc}', flush=True)
            entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
            failed.append(stock["code"])
            state["attempts"].append(entry)
            save_state(state)
            continue
        state["coverage"][stock["code"]] = stock["period"]
        entry["status"] = "success"
        state["attempts"].append(entry)
        save_state(state)
        if already:
            publish([STATE], f'auto-update: recheck {stock["code"]}')
            continue
        publish([report_path(stock), STATE], f'auto-update: {stock["name"]} {stock["period"]}')
        done.append(stock)
    if done:
        subprocess.run([sys.executable, "scripts/sync_ghpages.py"], cwd=ROOT, check=True)
        publish(["docs", STATE], "auto-update: refresh Pages indexes")
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        record_updates([{"name": s["name"], "code": s["code"], "period": s["period"],
                         "file": report_path(s).as_posix(), "commit": commit} for s in done])
    if failed:
        if not done:
            publish([STATE], f'auto-update: failed {"/".join(failed)}')
        raise RuntimeError(f"Failed reports (will retry on a later check): {failed}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Only check for uncovered reports (default)")
    parser.add_argument("--generate-only", action="store_true", help="Generate one report into --outdir")
    parser.add_argument("--publish", metavar="DIR", help="Publish reports from a results directory")
    parser.add_argument("--code", help="Stock code for --generate-only")
    parser.add_argument("--outdir", default="results", help="Output directory for --generate-only")
    parser.add_argument("--queue-out", help="Write the plan queue as JSON to this file")
    parser.add_argument("--manual", action="store_true", help="Ignore the daily attempt budget")
    args = parser.parse_args()
    if args.publish:
        publish_results(args.publish)
        return
    if args.generate_only:
        generate_one(args.code, args.outdir)
        return
    now = dt.datetime.now(TZ)
    config = read_json(ROOT / "watchlist.json")
    if not config["stocks"]:
        print("Watchlist empty")
        return
    schedule = os.environ.get("SCHEDULE_CRON")
    if schedule and schedule != expected_schedule(now):
        print("Inactive Sydney daylight-saving schedule; skipping")
        queue = []
    else:
        state = read_json(ROOT / STATE, {"coverage": {}, "attempts": []})
        manual = args.manual or os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        rows = calendar(config["stocks"], now.date())
        force = os.environ.get("FORCE_CODE", "").strip()
        if force and manual:
            queue = forced_plan(config, rows, now.date(), force)
        else:
            queue = plan(config, state, rows, now.date(), manual)
    print(json.dumps(queue, ensure_ascii=False, indent=2), flush=True)
    if args.queue_out:
        Path(args.queue_out).write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"count={len(queue)}\n")
            output.write("queue=" + json.dumps(queue, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
