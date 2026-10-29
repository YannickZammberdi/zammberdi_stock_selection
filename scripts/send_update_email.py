#!/usr/bin/env python3
"""Send a single summary email containing only successfully pushed stock reports."""
from email.message import EmailMessage
import argparse
from html import escape
import json
import os
from pathlib import Path
import smtplib
import ssl
from urllib.parse import quote


def build_message(reports, sender, recipient, repository, run_id):
    if not reports:
        raise ValueError("No successful reports to notify")
    owner, repo = repository.split("/", 1)
    base = f"https://{owner.lower()}.github.io/{quote(repo)}/"
    run_url = f"https://github.com/{repository}/actions/runs/{quote(run_id)}"
    lines = [f"本次成功更新 {len(reports)} 份个股报告：", ""]
    items = []
    for report in reports:
        path = report["file"]
        if not path.startswith("docs/stocks/") or ".." in path.split("/"):
            raise ValueError("Unexpected report path")
        url = base + quote(path.removeprefix("docs/"), safe="/")
        source = f'https://github.com/{repository}/blob/{quote(report["commit"], safe="")}/{quote(path, safe="/")}'
        title = f'{report["name"]}（{report["code"]}）— 财报截至 {report["period"]}'
        lines.extend([title, f"报告：{url}", f"已提交版本：{source}", ""])
        items.append(f'<li>{escape(title)}<br><a href="{escape(url, quote=True)}">查看报告</a>'
                     f' · <a href="{escape(source, quote=True)}">已提交版本</a></li>')
    note = "Pages 页面可能需要等待部署；若仍是旧版，请先查看已提交版本。"
    lines.extend([note, f"运行详情：{run_url}"])
    message = EmailMessage()
    message["Subject"] = f"个股报告已更新：{'、'.join(r['name'] for r in reports)}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(lines))
    message.add_alternative(
        f'<p>本次成功更新 {len(reports)} 份个股报告：</p><ul>{"".join(items)}</ul>'
        f'<p>{escape(note)}</p><p><a href="{escape(run_url, quote=True)}">运行详情</a></p>', subtype="html")
    return message


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Send a labeled test using a real report link')
    args = parser.parse_args(argv)
    reports = json.loads(os.environ.get("UPDATED_REPORTS", "[]"))
    if args.test:
        root = Path(__file__).resolve().parents[1]
        stock = json.loads((root / "watchlist.json").read_text(encoding="utf-8"))["stocks"][0]
        reports = [{"name": stock["name"], "code": stock["code"], "period": stock["covered_period"],
                    "file": f'docs/stocks/{stock["name"]}_{stock["code"]}_分析报告.html',
                    "commit": os.environ["GITHUB_SHA"]}]
    if not reports:
        return
    username = os.environ.get("SMTP_USERNAME", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("Configure GitHub secrets SMTP_USERNAME and SMTP_PASSWORD to enable email")
    message = build_message(reports, username, os.environ["MAIL_TO"],
                            os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_RUN_ID"])
    if args.test:
        message.replace_header("Subject", "【测试邮件·未触发报告更新】报告链接通知")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    context = ssl.create_default_context()
    if port == 465:
        connection = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
    else:
        connection = smtplib.SMTP(host, port, timeout=30)
    with connection as smtp:
        if port != 465:
            smtp.starttls(context=context)
        smtp.login(username, password)
        smtp.send_message(message)
    print(f"Email sent for {len(reports)} successful report(s)")


if __name__ == "__main__":
    main()
