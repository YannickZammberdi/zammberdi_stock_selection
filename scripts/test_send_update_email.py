import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from auto_update_stocks import record_updates
from send_update_email import build_message, main


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.reports = [{"name": "药明康德", "code": "603259", "period": "2026-09-30",
                         "file": "docs/stocks/药明康德_603259_分析报告.html", "commit": "abcdef"}]

    def test_links_and_recipient(self):
        message = build_message(self.reports, "sender@example.com", "xuexccc@gmail.com", "Owner/repo", "123")
        self.assertEqual(message["To"], "xuexccc@gmail.com")
        self.assertIn("药明康德", message["Subject"])
        html = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn("https://owner.github.io/repo/stocks/%E8%8D%AF", html)
        self.assertIn("/blob/abcdef/docs/stocks/", html)
        self.assertIn("/actions/runs/123", html)

    def test_no_success_no_smtp(self):
        with patch.dict(os.environ, {"UPDATED_REPORTS": "[]"}, clear=True):
            with patch("send_update_email.smtplib.SMTP") as smtp:
                main()
                smtp.assert_not_called()

    def test_missing_credentials_explicit_failure(self):
        with patch.dict(os.environ, {"UPDATED_REPORTS": '[{"name":"test"}]'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SMTP_USERNAME"):
                main()

    def test_success_output_is_single_line_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "output"
            with patch.dict(os.environ, {"GITHUB_OUTPUT": str(path)}):
                record_updates(self.reports)
            self.assertEqual(len(path.read_text().splitlines()), 1)
            self.assertTrue(path.read_text().startswith("updated=["))


if __name__ == "__main__":
    unittest.main()
