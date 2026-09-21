import copy
import httpx
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


TEST_DATA_ROOT = tempfile.TemporaryDirectory()
os.environ["LOCALAPPDATA"] = TEST_DATA_ROOT.name

import smart_voice_typing as app


class SmartVoiceTypingTests(unittest.TestCase):
    def setUp(self):
        app.state.config = copy.deepcopy(app.DEFAULT_CONFIG)
        app.state.glossary = {}
        app.state.used_seconds = 0.0
        app.state.used_requests = 0
        app.state.hourly_seconds = {}
        app.state.minute_requests = []
        app.state.last_result = ""
        app.state.ui_queue = app.queue.Queue()

    def test_source_and_default_config_do_not_contain_groq_key(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertNotIn("gsk_", source)
        self.assertEqual(app.DEFAULT_CONFIG["api_key"], "")

    def test_logs_do_not_include_transcribed_or_prompt_content(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertNotIn('log_message(f"F8 (Gốc):', source)
        self.assertNotIn('log_message(f"AI đang xử lý:', source)

    def test_legacy_log_sanitizer_removes_only_sensitive_entries(self):
        log_file = Path(TEST_DATA_ROOT.name) / "legacy.log"
        log_file.write_text(
            "INFO startup ok\nINFO F8 (Gốc): 'bí mật'\nERROR network failed\n",
            encoding="utf-8",
        )

        removed = app.sanitize_legacy_logs(log_file)

        self.assertEqual(removed, 1)
        sanitized = log_file.read_text(encoding="utf-8")
        self.assertIn("startup ok", sanitized)
        self.assertIn("network failed", sanitized)
        self.assertNotIn("bí mật", sanitized)

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

    def test_recording_limit_uses_monotonic_elapsed_time(self):
        self.assertFalse(app.recording_limit_reached(100.0, 300.0, now=399.99))
        self.assertTrue(app.recording_limit_reached(100.0, 300.0, now=400.0))

    def make_api(self, transcription="xin chào", completion="Hello."):
        transcriptions = mock.Mock()
        transcriptions.create.return_value = transcription
        completions = mock.Mock()
        completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=completion))]
        )
        api = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=transcriptions),
            chat=SimpleNamespace(completions=completions),
        )
        return api, transcriptions, completions

    def run_f8(self, api):
        audio = app.np.full(app.SAMPLE_RATE, 1000, dtype=app.np.int16)
        with (
            mock.patch.object(app, "get_client", return_value=api),
            mock.patch.object(app, "normalize_audio", side_effect=lambda value: value),
            mock.patch.object(app, "check_limits", return_value=(True, "")) as check_limits,
            mock.patch.object(app, "record_usage"),
            mock.patch.object(app, "get_active_window_context", return_value="CƠ BẢN"),
            mock.patch.object(app, "update_status"),
            mock.patch.object(app.clipboard_manager, "paste_text") as paste_text,
        ):
            app.process_audio(audio)
        return check_limits, paste_text

    def test_f8_raw_mode_uses_one_request_and_skips_chat(self):
        api, _transcriptions, completions = self.make_api(transcription="xin chào")

        check_limits, paste_text = self.run_f8(api)

        check_limits.assert_called_once_with(1.0, 1)
        completions.create.assert_not_called()
        paste_text.assert_called_once_with("xin chào", None)

    def test_f8_translation_setting_is_applied(self):
        app.state.config["translation_mode"] = "Việt -> Anh"
        api, _transcriptions, completions = self.make_api(completion="Hello.")

        check_limits, paste_text = self.run_f8(api)

        check_limits.assert_called_once_with(1.0, 2)
        completions.create.assert_called_once()
        paste_text.assert_called_once_with("Hello.", None)

    def test_f8_smart_punctuation_setting_is_applied(self):
        app.state.config["smart_punctuation"] = True
        api, _transcriptions, completions = self.make_api(completion="Xin chào.")

        check_limits, paste_text = self.run_f8(api)

        check_limits.assert_called_once_with(1.0, 2)
        completions.create.assert_called_once()
        paste_text.assert_called_once_with("Xin chào.", None)

    @mock.patch.object(app, "send_unicode_text")
    @mock.patch.object(app.win32gui, "IsWindow", return_value=True)
    @mock.patch.object(app.win32gui, "GetForegroundWindow", return_value=123)
    def test_text_delivery_types_only_into_original_window(self, _foreground, _is_window, send_text):
        delivered = app.clipboard_manager.paste_text("Kết quả", target_hwnd=123)

        self.assertTrue(delivered)
        self.assertEqual(app.state.last_result, "Kết quả")
        send_text.assert_called_once_with("Kết quả")

    @mock.patch.object(app, "send_unicode_text")
    @mock.patch.object(app.win32gui, "IsWindow", return_value=True)
    @mock.patch.object(app.win32gui, "GetForegroundWindow", return_value=456)
    def test_text_delivery_keeps_result_when_focus_changed(self, _foreground, _is_window, send_text):
        delivered = app.clipboard_manager.paste_text("Kết quả", target_hwnd=123)

        self.assertFalse(delivered)
        self.assertEqual(app.state.last_result, "Kết quả")
        send_text.assert_not_called()

    def test_selected_text_restores_original_ole_clipboard(self):
        old_clipboard = object()
        with (
            mock.patch.object(app.pythoncom, "CoInitialize"),
            mock.patch.object(app.pythoncom, "CoUninitialize"),
            mock.patch.object(app.pythoncom, "OleGetClipboard", return_value=old_clipboard),
            mock.patch.object(app.pythoncom, "OleSetClipboard") as restore_clipboard,
            mock.patch.object(app.win32clipboard, "GetClipboardSequenceNumber", side_effect=[10, 11]),
            mock.patch.object(app.keyboard, "send"),
            mock.patch.object(app.pyperclip, "paste", return_value="đoạn được chọn"),
        ):
            selected = app.get_selected_text()

        self.assertEqual(selected, "đoạn được chọn")
        restore_clipboard.assert_called_once_with(old_clipboard)

    def test_wait_for_hotkey_release(self):
        with mock.patch.object(app.keyboard, "is_pressed", side_effect=[True, False]):
            self.assertTrue(app.wait_for_hotkey_release("ctrl+alt+f9", timeout=1.0))

    def test_user_error_messages_are_actionable(self):
        request = httpx.Request("POST", "https://api.groq.com/test")
        auth_response = httpx.Response(401, request=request)
        rate_response = httpx.Response(429, request=request)
        auth_error = app.AuthenticationError("unauthorized", response=auth_response, body=None)
        rate_error = app.RateLimitError("limited", response=rate_response, body=None)
        network_error = app.APIConnectionError(request=request)

        self.assertIn("API KEY", app.user_error_message(auth_error))
        self.assertIn("GIỚI HẠN", app.user_error_message(rate_error))
        self.assertIn("INTERNET", app.user_error_message(network_error))

    def test_ui_does_not_use_background_threading_timers(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertNotIn("threading.Timer", source)

    def test_tts_health_uses_windows_sapi(self):
        voices = SimpleNamespace(Count=1)
        voice = SimpleNamespace(GetVoices=mock.Mock(return_value=voices))
        with (
            mock.patch.object(app.pythoncom, "CoInitialize"),
            mock.patch.object(app.pythoncom, "CoUninitialize"),
            mock.patch.object(app, "init_tts", return_value=voice),
        ):
            available, backend = app.tts_health_check()

        self.assertTrue(available)
        self.assertEqual(backend, "Windows SAPI")


if __name__ == "__main__":
    unittest.main()
