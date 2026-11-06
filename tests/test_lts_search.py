import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "troubleshoot-lts-logs" / "scripts" / "lts_search.py"
spec = importlib.util.spec_from_file_location("lts_search", SCRIPT)
lts = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lts
spec.loader.exec_module(lts)


class SigningTests(unittest.TestCase):
    def test_signature_matches_independent_canonical(self):
        url = "https://lts.example.com/v2/p/groups/g1/streams/s1/content/query?b=2&a=1"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Project-Id": "p",
            "X-Sdk-Content-Sha256": "UNSIGNED-PAYLOAD",
            "X-Sdk-Date": "20260101T000000Z",
        }
        body = b'{"q":1}'
        _, signed = lts.sign_request("POST", url, headers, body, "AK", "SK")

        # Independent canonical construction for cross-check.
        canonical_headers = (
            "content-type:application/json;charset=UTF-8\n"
            "host:lts.example.com\n"
            "x-project-id:p\n"
            "x-sdk-content-sha256:UNSIGNED-PAYLOAD\n"
            "x-sdk-date:20260101T000000Z\n"
        )
        names = "content-type;host;x-project-id;x-sdk-content-sha256;x-sdk-date"
        canonical_request = "\n".join((
            "POST",
            "/v2/p/groups/g1/streams/s1/content/query/",
            "a=1&b=2",
            canonical_headers,
            names,
            "UNSIGNED-PAYLOAD",
        ))
        import hashlib
        import hmac
        request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
        string_to_sign = f"SDK-HMAC-SHA256\n20260101T000000Z\n{request_hash}"
        expected = hmac.new(b"SK", string_to_sign.encode(), hashlib.sha256).hexdigest()

        self.assertIn(f"Signature={expected}", signed["Authorization"])
        self.assertIn("Access=AK", signed["Authorization"])
        self.assertEqual(signed["host"], "lts.example.com")
        self.assertEqual(signed["content-length"], str(len(body)))


class TimeParsingTests(unittest.TestCase):
    def test_naive_iso_uses_shanghai(self):
        # 2026-11-06 10:00 Asia/Shanghai (UTC+8) == 2026-11-06 02:00 UTC
        self.assertEqual(lts.parse_time("2026-11-06 10:00"), 1793930400000)

    def test_epoch_seconds_and_millis(self):
        self.assertEqual(lts.parse_time("1793930400"), 1793930400000)
        self.assertEqual(lts.parse_time("1793930400000"), 1793930400000)

    def test_invalid_raises(self):
        with self.assertRaises(lts.CliError):
            lts.parse_time("not-a-time")


class NormalizeTests(unittest.TestCase):
    def test_normalizes_and_redacts(self):
        item = {
            "content": '{"time":"2026-11-04 09:50:42.791","level":"ERROR","message":"Authorization: abc\\nboom","TID":"[TID:xyz]"}',
            "labels": {"podName": "pod-1", "level": "<HighLightTag>ERROR</HighLightTag>"},
            "line_num": "123",
        }
        result = lts._normalize(item)
        self.assertEqual(result["level"], "ERROR")
        self.assertEqual(result["TID"], "[TID:xyz]")
        self.assertNotIn("abc", result["message"])

    def test_truncates_long_messages(self):
        item = {"content": '{"message":"' + "x" * 9000 + '"}'}
        result = lts._normalize(item)
        self.assertTrue(result["messageTruncated"])
        self.assertLess(len(result["message"]), 8100)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.settings = lts.Settings(
            ak="a", sk="s", project_id="p",
            group_map={"robot-business": "g1"}, node_map={"robot-business-device": "s1"},
        )

    def _call(self, **kwargs):
        params = dict(group="robot-business", node="robot-business-device",
                      start_time="2026-11-06 10:00", end_time="2026-11-06 10:30",
                      keywords="boom", limit=100)
        params.update(kwargs)
        return lts.search(self.settings, **params)

    def test_rejects_range_over_two_hours(self):
        with self.assertRaises(lts.CliError):
            self._call(end_time="2026-11-06 12:00:01")

    def test_rejects_bad_limit(self):
        with self.assertRaises(lts.CliError):
            self._call(limit=101)

    def test_rejects_unknown_group_without_network(self):
        with self.assertRaises(lts.CliError) as ctx:
            self._call(group="nope")
        self.assertIn("available", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
