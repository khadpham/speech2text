import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_DATA_ROOT = tempfile.TemporaryDirectory()
os.environ["LOCALAPPDATA"] = TEST_DATA_ROOT.name

import smart_voice_typing as app


class SmartVoiceTypingTests(unittest.TestCase):
    def setUp(self):
        app.state.glossary = {}
        app.state.used_seconds = 0.0
        app.state.used_requests = 0
        app.state.hourly_seconds = {}
        app.state.minute_requests = []

    def test_source_and_default_config_do_not_contain_groq_key(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertNotIn("gsk_", source)
        self.assertEqual(app.DEFAULT_CONFIG["api_key"], "")

    def test_dpapi_round_trip(self):
        encrypted = app.protect_secret("test-secret")
        self.assertNotEqual(encrypted, "test-secret")
        self.assertEqual(app.unprotect_secret(encrypted), "test-secret")

    def test_glossary_replacement_treats_backslashes_literally(self):
        app.state.glossary = {"folder": r"C:\new\folder"}
        self.assertEqual(app.apply_glossary("Open FOLDER"), r"Open C:\new\folder")

    @mock.patch.object(app.subprocess, "Popen")
    def test_action_allowlist_blocks_command_injection(self, popen):
        result = app.execute_action("ACTION: OPEN calc & del *")
        self.assertIn("chưa được cho phép", result)
        popen.assert_not_called()

    @mock.patch.object(app.webbrowser, "open")
    def test_search_query_is_url_encoded(self, browser_open):
        app.execute_action("ACTION: SEARCH thời tiết & tin tức")
        url = browser_open.call_args.args[0]
        self.assertIn("%26", url)
        self.assertNotIn(" & ", url)

    def test_limit_check_counts_all_requests(self):
        app.state.used_requests = app.LIMIT_RPD - 1
        allowed, _ = app.check_limits(0, request_count=2)
        self.assertFalse(allowed)

    def test_current_model_ids_are_configured(self):
        self.assertEqual(app.DEFAULT_CONFIG["assistant_model"], "qwen/qwen3.8-27b")
        self.assertEqual(app.DEFAULT_CONFIG["transcription_model"], "whisper-large-v3")

    def test_hotkey_validation(self):
        self.assertTrue(app.is_valid_hotkey("ctrl+f8"))
        self.assertFalse(app.is_valid_hotkey("not-a-real-key"))


if __name__ == "__main__":
    unittest.main()
