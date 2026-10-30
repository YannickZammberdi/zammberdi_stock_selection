import datetime as dt
from pathlib import Path
import re
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import auto_update_stocks as updater


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(updater, "ROOT", Path(self.temp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.today = dt.date(2026, 10, 29)
        self.stock = {"code": "603259", "name": "药明康德", "covered_period": "2026-06-30"}
        self.config = {"stocks": [self.stock], "daily_limit": 5}
        self.state = {"coverage": {}, "attempts": []}

    def row(self, period="2026-09-30", published="2026-10-27", flag="1"):
        return {"SECURITY_CODE": "603259", "REPORT_DATE": period,
                "ACTUAL_PUBLISH_DATE": published, "IS_PUBLISH": flag}

    def plan(self, rows, manual=False):
        return updater.plan(self.config, self.state, rows, self.today, manual)

    def fail_reserve(self):
        raise AssertionError("paid fallback must not be reserved")

    def test_catches_old_disclosure_not_only_yesterday(self):
        self.assertEqual(len(self.plan([self.row()])), 1)

    def test_never_runs_future_same_day_or_appointment_only(self):
        for published, flag in [("2026-10-30", "1"), ("2026-10-29", "1"), ("", "0")]:
            self.assertFalse(self.plan([self.row(published=published, flag=flag)]))

    def test_skip_covered_period(self):
        self.state["coverage"]["603259"] = "2026-09-30"
        self.assertFalse(self.plan([self.row()]))

    def test_skip_already_covered_initial_report(self):
        self.assertFalse(self.plan([self.row(period="2026-06-30")]))

    def test_latest_only(self):
        self.stock["covered_period"] = "2025-12-31"
        rows = [self.row(period="2026-06-30", published="2026-08-25"), self.row()]
        self.assertEqual([s["period"] for s in self.plan(rows)], ["2026-09-30"])

    def test_cap_includes_failures_and_in_progress(self):
        self.state["attempts"] = [{"day": "2026-10-29", "status": "failed"}] * 5
        self.assertFalse(self.plan([self.row()]))
        self.state["attempts"] = [{"day": "2026-10-28"}] * 5
        self.assertEqual(len(self.plan([self.row()])), 1)

    def test_cap_five_even_if_config_larger(self):
        self.config["daily_limit"] = 99
        self.config["stocks"] = [{**self.stock, "code": str(i)} for i in range(10)]
        rows = [{**self.row(), "SECURITY_CODE": str(i)} for i in range(10)]
        self.assertEqual(len(self.plan(rows)), 5)

    def test_ignores_pool_outsiders(self):
        self.assertFalse(self.plan([{**self.row(), "SECURITY_CODE": "600309"}]))

    def test_analysis_date_is_not_coverage(self):
        path = updater.ROOT / updater.report_path(self.stock)
        path.parent.mkdir(parents=True)
        path.write_text('分析日期：2026-10-28', encoding="utf-8")
        self.assertEqual(len(self.plan([self.row()])), 1)
        path.write_text('<!-- COVERAGE period=2026-09-30 -->', encoding="utf-8")
        self.assertFalse(self.plan([self.row()]))

    def test_invalid_generated_html_is_rejected(self):
        with self.assertRaises(ValueError):
            updater.validate("<html>nothing</html>", "2026-09-30", "old")

    def report(self, coverage="", meta="分析日期：2026-10-30"):
        tabs = "".join(f'<div id="tab-{t}"></div>' for t in
                       ("summary", "l1", "l2", "l3", "l4", "l5", "l6"))
        return (f'<html><head></head><body><p class="meta">{meta}</p>{coverage}{tabs}'
                '94/100<!-- TRACK fwd=A rating=Buy node=x --><!-- HISTORY-TABLE -->'
                '<table></table></body></html>')

    def test_marker_with_unusual_whitespace_is_accepted(self):
        coverage = '<!--\u3000COVERAGE\u00a0period=2026-09-30\u3000-->'
        result = updater.validate(self.report(coverage), "2026-09-30", "old")
        self.assertIn("<!-- COVERAGE period=2026-09-30 -->", result)

    def test_marker_injected_when_meta_states_the_period(self):
        meta = "分析日期：2026-10-30 | 数据截止：2026 年三季报（2026-09-30，2026-10-27 披露）"
        result = updater.validate(self.report(meta=meta), "2026-09-30", "old")
        self.assertIn("<!-- COVERAGE period=2026-09-30 -->", result)
        # The analysis date must stay the first date sync_ghpages sees.
        self.assertEqual(updater.dt.date.fromisoformat("2026-10-30").isoformat(),
                         re.search(r"(\d{4}-\d{2}-\d{2})", result).group(1))

    def test_marker_not_injected_without_period_evidence(self):
        with self.assertRaisesRegex(ValueError, "coverage marker"):
            updater.validate(self.report(), "2026-09-30", "old")

    def test_marker_for_another_period_is_rejected(self):
        coverage = "<!-- COVERAGE period=2026-06-30 -->"
        with self.assertRaisesRegex(ValueError, "does not match"):
            updater.validate(self.report(coverage), "2026-09-30", "old")

    def test_fullwidth_marker_prevents_regeneration(self):
        path = updater.ROOT / updater.report_path(self.stock)
        path.parent.mkdir(parents=True)
        path.write_text('<!--\u3000COVERAGE period=2026-09-30 -->', encoding="utf-8")
        self.assertFalse(self.plan([self.row()]))

    def test_manual_run_ignores_daily_budget(self):
        self.state["attempts"] = [{"day": "2026-10-29", "status": "failed"}] * 5
        self.assertFalse(self.plan([self.row()]))
        self.assertEqual(len(self.plan([self.row()], manual=True)), 1)

    def test_opencode_workspace_env_overrides_pwd(self):
        env = updater.workspace_env(r"/tmp/clone")
        self.assertEqual(env["PWD"], "/tmp/clone")

    def test_forced_plan_ignores_coverage(self):
        self.state["coverage"]["603259"] = "2026-09-30"
        queue = updater.forced_plan(self.config, [self.row()], self.today, "603259")
        self.assertEqual([(s["code"], s["period"]) for s in queue], [("603259", "2026-09-30")])
        with self.assertRaises(SystemExit):
            updater.forced_plan(self.config, [self.row()], self.today, "600309")

    def test_sydney_dst_schedule(self):
        for month, hour in [(1, 21), (7, 22), (10, 21)]:
            now = dt.datetime(2026, month, 15, 8, 30, tzinfo=updater.TZ)
            self.assertEqual(updater.expected_schedule(now), f"30 {hour} * * *")

    def test_sydney_dst_transition_days(self):
        for month, day, hour in [(4, 4, 21), (4, 5, 22), (10, 3, 22), (10, 4, 21)]:
            now = dt.datetime(2026, month, day, 8, 30, tzinfo=updater.TZ)
            self.assertEqual(updater.expected_schedule(now), f"30 {hour} * * *")

    def test_primary_success_no_paid_call(self):
        config = {"model": "free", "fallback_model": "deepseek/official"}
        with patch.object(updater, "generate") as generate:
            self.assertEqual(updater.generate_with_fallback(self.stock, config), ("free", False))
            generate.assert_called_once_with(self.stock, "free")

    def test_timeout_never_switches_to_paid(self):
        config = {"model": "free", "fallback_model": "deepseek/official"}
        with patch.object(updater, "generate",
                          side_effect=subprocess.TimeoutExpired("opencode", 600)) as generate:
            with patch.dict(updater.os.environ, {"DEEPSEEK_API_KEY": "test"}):
                with self.assertRaises(subprocess.TimeoutExpired):
                    updater.generate_with_fallback(self.stock, config, reserve=self.fail_reserve)
        self.assertEqual(generate.call_count, 1)

    def test_bad_report_retries_free_model_without_paying(self):
        config = {"model": "free", "fallback_model": "deepseek/official"}
        with patch.object(updater, "generate", side_effect=[ValueError("bad HTML"), None]) as generate:
            with patch.dict(updater.os.environ, {"DEEPSEEK_API_KEY": "test"}):
                result = updater.generate_with_fallback(self.stock, config, reserve=self.fail_reserve)
        self.assertEqual(result, ("free", False))
        self.assertEqual([c.args[1] for c in generate.call_args_list], ["free", "free"])

    def test_quota_error_switches_to_paid(self):
        config = {"model": "free", "fallback_model": "deepseek/official"}
        with patch.object(updater, "generate",
                          side_effect=[updater.ModelUnavailable("429 rate limit"), None]) as generate:
            with patch.dict(updater.os.environ, {"DEEPSEEK_API_KEY": "test"}):
                result = updater.generate_with_fallback(self.stock, config)
        self.assertEqual(result, ("deepseek/official", True))
        self.assertEqual([c.args[1] for c in generate.call_args_list], ["free", "deepseek/official"])

    def test_quota_detection_patterns(self):
        for text in ("429 Too Many Requests", "daily quota exceeded", "余额不足", "rate_limit_exceeded",
                     "insufficient credits", "用量上限已达"):
            self.assertTrue(updater.QUOTA_RE.search(text), text)
        for text in ("model returned invalid JSON", "opencode exited with 1: timeout"):
            self.assertFalse(updater.QUOTA_RE.search(text), text)

    def test_fallback_requires_secret(self):
        config = {"model": "free", "fallback_model": "deepseek/official"}
        with patch.object(updater, "generate", side_effect=updater.ModelUnavailable("quota")) as generate:
            with patch.dict(updater.os.environ, {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "DEEPSEEK_API_KEY"):
                    updater.generate_with_fallback(self.stock, config)
                self.assertEqual(generate.call_count, 1)

    def test_paid_fallback_skipped_after_daily_limit(self):
        config = {"model": "free", "fallback_model": "deepseek/official", "fallback_daily_limit": 1}
        with patch.object(updater, "generate", side_effect=[updater.ModelUnavailable("quota"), None]) as generate:
            with patch.dict(updater.os.environ, {"DEEPSEEK_API_KEY": "test"}):
                self.assertEqual(updater.generate_with_fallback(self.stock, config, allow_paid=False), ("free", False))
                self.assertEqual([c.args[1] for c in generate.call_args_list], ["free", "free"])

    def test_paid_fallback_count_resets_next_day(self):
        state = {"attempts": [
            {"day": "2026-10-29", "paid_fallback": True},
            {"day": "2026-10-30", "paid_fallback": True},
            {"day": "2026-10-30", "paid_fallback": False},
        ]}
        self.assertEqual(updater.paid_fallback_used(state, "2026-10-30"), 1)
        self.assertEqual(updater.paid_fallback_used(state, "2026-10-31"), 0)

    def test_paid_fallback_reserves_before_spending(self):
        config = {"model": "free", "fallback_model": "deepseek/official"}
        calls = []
        with patch.object(updater, "generate",
                          side_effect=[updater.ModelUnavailable("quota"), None]) as generate:
            with patch.dict(updater.os.environ, {"DEEPSEEK_API_KEY": "test"}):
                result = updater.generate_with_fallback(self.stock, config, reserve=lambda: calls.append("reserved"))
        self.assertEqual(result, ("deepseek/official", True))
        self.assertEqual(calls, ["reserved"])
        self.assertEqual(generate.call_count, 2)

    def test_paid_reservation_does_not_eat_daily_update_budget(self):
        self.state["attempts"] = [
            {"day": "2026-10-29", "status": "paid-reservation", "paid_fallback": True},
            {"day": "2026-10-29", "status": "success"},
        ]
        self.assertEqual(len(self.plan([self.row()])), 1)

    def test_no_fallback_retries_free_model_instead_of_paying(self):
        config = {"model": "opencode/free"}
        with patch.object(updater, "generate", side_effect=[ValueError("bad HTML"), None]) as generate:
            with patch.dict(updater.os.environ, {}, clear=True):
                self.assertEqual(updater.generate_with_fallback(self.stock, config), ("opencode/free", False))
                self.assertEqual([c.args[1] for c in generate.call_args_list], ["opencode/free", "opencode/free"])


if __name__ == "__main__":
    unittest.main()
