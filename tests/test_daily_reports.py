import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SHEET = "小组,姓名,5.20,5.21\n运营组,张三,昨天的日报,今天的日报\n,李四,昨天的日报,\n"


class DailyReportDateTests(unittest.TestCase):
    def test_parse_daily_uses_only_requested_date_and_labels_it(self):
        script = ROOT / "daily-report/scripts/parse_daily.py"
        for date, success in (("5.21", True), ("5.22", False)):
            with self.subTest(date=date):
                result = subprocess.run(
                    ["python3", str(script), date, "--group=运营组"],
                    input=json.dumps({"csv_data": SHEET}),
                    text=True,
                    capture_output=True,
                )
                if success:
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(result.stdout.splitlines()[0], "实际日期：5月21日")
                    self.assertIn("今天的日报", result.stdout)
                    self.assertNotIn("昨天的日报", result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("5.22 日期列不存在", result.stderr)

    def test_check_daily_uses_only_requested_date_and_labels_it(self):
        script = ROOT / "check-daily-report/scripts/check_daily.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_mcporter = Path(temp_dir) / "mcporter"
            fake_mcporter.write_text("#!/bin/sh\ncat \"$MOCK_SHEET_DATA\"\n")
            fake_mcporter.chmod(0o755)
            data_file = Path(temp_dir) / "sheet.json"
            data_file.write_text(json.dumps({"csv_data": SHEET}))
            env = {**os.environ, "PATH": f"{temp_dir}:{os.environ['PATH']}", "MOCK_SHEET_DATA": str(data_file)}
            for date, success in (("5.21", True), ("5.22", False)):
                with self.subTest(date=date):
                    result = subprocess.run(
                        ["python3", str(script), date, "--group=运营组", "--url=https://docs.qq.com/sheet/demo?tab=sheet1"],
                        text=True,
                        capture_output=True,
                        env=env,
                    )
                    if success:
                        self.assertEqual(result.returncode, 0)
                        self.assertEqual(result.stdout.splitlines()[0], "实际日期：5月21日")
                        self.assertIn("- 李四", result.stdout)
                        self.assertNotIn("- 张三", result.stdout)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(result.stdout, "")
                        self.assertIn("5.22 日期列不存在", result.stderr)


if __name__ == "__main__":
    unittest.main()
