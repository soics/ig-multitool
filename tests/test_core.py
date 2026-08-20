"""Unit tests for IG Multi-Tool core logic.

Runs with the stdlib test runner (no pytest dependency):

    python -m unittest discover -s tests -v

Covers: config merging, actions pacing/progress/login, the AI chat loop
against FakeClient, and the non-mutual / group detection filters.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import actions  # noqa: E402
import ai_chat  # noqa: E402
import config as config_mod  # noqa: E402
import leave_chat  # noqa: E402
from fake_client import FakeClient  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_deep_merge_nested(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        merged = config_mod._deep_merge(base, {"a": {"y": 9}})
        self.assertEqual(merged, {"a": {"x": 1, "y": 9}, "b": 3})
        self.assertEqual(base, {"a": {"x": 1, "y": 2}, "b": 3})

    def test_deep_merge_scalar_replaces(self):
        base = {"whitelist": [], "ai": {"enabled": False}}
        merged = config_mod._deep_merge(base, {"whitelist": ["a"], "ai": "off"})
        self.assertEqual(merged, {"whitelist": ["a"], "ai": "off"})

    def test_load_config_merges_example_and_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            example = root / "config.example.json"
            example.write_text(
                '{"ai": {"enabled": true, "whitelist_only": true}, "whitelist": ["alexnova"]}',
                encoding="utf-8",
            )
            with patch("config.CONFIG_PATH", root / "config.json"), patch(
                "config.EXAMPLE_PATH", example
            ):
                cfg = config_mod.load_config()
        self.assertTrue(cfg["ai"]["enabled"])
        self.assertTrue(cfg["ai"]["whitelist_only"])
        self.assertEqual(cfg["ai"]["poll_interval_seconds"], 20)
        self.assertEqual(cfg["ai"]["model"], "ollama/gpt-oss:120b")
        self.assertEqual(cfg["whitelist"], ["alexnova"])
        self.assertTrue(Path(cfg["session_path"]).is_absolute())

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json"
            with patch("config.CONFIG_PATH", config_path), patch(
                "config.EXAMPLE_PATH", root / "config.example.json"
            ):
                config_mod.save_config({"ai": {"enabled": True}, "whitelist": ["x"]})
                cfg = config_mod.load_config()
        self.assertTrue(cfg["ai"]["enabled"])
        self.assertEqual(cfg["whitelist"], ["x"])
        self.assertEqual(cfg["pacing"]["action_delay_min"], 3)


class ActionsTests(unittest.TestCase):
    def test_human_count(self):
        import re

        plain = lambda n: re.sub(r"\x1b\[[0-9;]*m", "", actions.human_count(n))
        self.assertIn("1 account", plain(1))
        self.assertIn("3 accounts", plain(3))

    def test_sleep_between_actions(self):
        with patch("actions.time.sleep") as sleep, patch(
            "actions.random.uniform", return_value=2.5
        ):
            actions.sleep_between_actions({"pacing": {"action_delay_min": 1, "action_delay_max": 3}})
        sleep.assert_called_once_with(2.5)

    def test_maybe_batch_pause(self):
        cfg = {"pacing": {"batch_pause_every": 2, "batch_pause_seconds": 5}}
        with patch("actions.time.sleep") as sleep:
            actions.maybe_batch_pause(cfg, done=2)
            sleep.assert_called_once_with(5)
        with patch("actions.time.sleep") as sleep:
            actions.maybe_batch_pause(cfg, done=1)
            sleep.assert_not_called()
        with patch("actions.time.sleep") as sleep:
            actions.maybe_batch_pause({"pacing": {"batch_pause_every": 0, "batch_pause_seconds": 5}}, done=2)
            sleep.assert_not_called()

    def test_done_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "done.txt")
            actions.append_done(path, "alexnova")
            actions.append_done(path, "brianna_k")
            self.assertEqual(actions.read_done_file(path), {"alexnova", "brianna_k"})
        self.assertEqual(actions.read_done_file(path), set())

    def test_login_verifies_session_without_relogin(self):
        class RecordingClient:
            def __init__(self):
                self.calls = []

            def load_settings(self, path):
                self.calls.append(("load_settings", path))

            def account_info(self):
                self.calls.append(("account_info",))

            def login(self, username, password):
                self.calls.append(("login", username, password))

            def dump_settings(self, path):
                self.calls.append(("dump_settings", path))

        with tempfile.TemporaryDirectory() as tmp:
            session = str(Path(tmp) / "session.json")
            Path(session).write_text("{}", encoding="utf-8")
            client = actions.login(lambda: RecordingClient(), {"session_path": session})
            names = [call[0] for call in client.calls]
        self.assertIn("load_settings", names)
        self.assertIn("account_info", names)
        self.assertNotIn("login", names)

    def test_login_falls_back_when_session_invalid(self):
        class RecordingClient:
            def __init__(self):
                self.calls = []

            def load_settings(self, path):
                self.calls.append(("load_settings", path))
                raise ValueError("corrupt session")

            def account_info(self):
                self.calls.append(("account_info",))

            def login(self, username, password):
                self.calls.append(("login", username, password))

            def dump_settings(self, path):
                self.calls.append(("dump_settings", path))

        with tempfile.TemporaryDirectory() as tmp:
            session = str(Path(tmp) / "session.json")
            Path(session).write_text("{}", encoding="utf-8")
            cfg = {"session_path": session, "username": "me", "password": "pw"}
            client = actions.login(lambda: RecordingClient(), cfg)
            names = [call[0] for call in client.calls]
        self.assertIn("login", names)
        self.assertIn("dump_settings", names)
        self.assertNotIn("account_info", names)

    def test_login_fresh_when_no_session(self):
        class RecordingClient:
            def __init__(self):
                self.calls = []

            def login(self, username, password):
                self.calls.append(("login", username, password))

            def dump_settings(self, path):
                self.calls.append(("dump_settings", path))

        with tempfile.TemporaryDirectory() as tmp:
            session = str(Path(tmp) / "session.json")
            cfg = {"session_path": session, "username": "me", "password": "pw"}
            client = actions.login(lambda: RecordingClient(), cfg)
        self.assertEqual(client.calls, [("login", "me", "pw"), ("dump_settings", session)])


def _cfg(whitelist=(), **ai_overrides):
    ai = {"enabled": False, "whitelist_only": False, "poll_interval_seconds": 20}
    ai.update(ai_overrides)
    return {"ai": ai, "whitelist": list(whitelist)}


class SendRecorder:
    def __init__(self, client, drop: bool = False):
        self.sent = []
        self._real = client.direct_send
        self._drop = drop

        def send(text, user_ids=(), thread_ids=(), **kwargs):
            self.sent.append(text)
            if not self._drop:
                return self._real(text, user_ids=user_ids, thread_ids=thread_ids, **kwargs)

        client.direct_send = send


class AiChatTests(unittest.TestCase):
    def _run_loop(self, client, cfg, iterations=2):
        sleeps = [None] * (iterations - 1) + [KeyboardInterrupt]
        with patch("ai_chat.time.sleep", side_effect=sleeps):
            ai_chat.chat_loop(client, cfg)

    def test_replies_to_new_incoming_message(self):
        client = FakeClient()
        recorder = SendRecorder(client)
        self._run_loop(client, _cfg())
        self.assertEqual(len(recorder.sent), 3)
        self.assertIn("alexnova", recorder.sent[0])
        self.assertIn("erik_w", recorder.sent[1])
        self.assertIn("fifi_draws", recorder.sent[2])
        thread = client.direct_thread("1001")
        self.assertTrue(thread.messages[-1].is_sent_by_viewer)
        self.assertIn("alexnova", thread.messages[-1].text)

    def test_no_double_reply_same_message(self):
        client = FakeClient()
        client._threads = [client.direct_thread("1001")]
        recorder = SendRecorder(client)
        self._run_loop(client, _cfg(), iterations=3)
        self.assertEqual(len(recorder.sent), 1)

    def test_ignores_own_messages(self):
        client = FakeClient()
        client._threads = [client.direct_thread("1001")]
        client._threads[0].messages = [
            m for m in client._threads[0].messages if m.is_sent_by_viewer
        ]
        recorder = SendRecorder(client, drop=True)
        self._run_loop(client, _cfg())
        self.assertEqual(recorder.sent, [])

    def test_skips_threads_without_text(self):
        client = FakeClient()
        client._threads = [client.direct_thread("1004")]
        recorder = SendRecorder(client, drop=True)
        self._run_loop(client, _cfg())
        self.assertEqual(recorder.sent, [])

    def test_whitelist_only_filters_non_whitelisted(self):
        client = FakeClient()
        recorder = SendRecorder(client, drop=True)
        self._run_loop(client, _cfg(whitelist=["brianna_k"], whitelist_only=True))
        self.assertEqual(recorder.sent, [])

    def test_whitelist_only_allows_whitelisted(self):
        client = FakeClient()
        recorder = SendRecorder(client)
        self._run_loop(client, _cfg(whitelist=["alexnova"], whitelist_only=True))
        self.assertEqual(len(recorder.sent), 1)
        self.assertIn("alexnova", recorder.sent[0])

    def test_send_failure_skips_thread_but_loop_continues(self):
        class FailFirst(FakeClient):
            def direct_send(self, text, user_ids=(), thread_ids=(), **kwargs):
                if "1001" in {str(t) for t in thread_ids}:
                    raise ValueError("boom")
                return super().direct_send(text, user_ids=user_ids, thread_ids=thread_ids, **kwargs)

        client = FailFirst()
        self._run_loop(client, _cfg())
        thread = client.direct_thread("1002")
        self.assertEqual(len(thread.messages), 2)

    def test_interrupt_during_send_exits_cleanly(self):
        class InterruptSend(FakeClient):
            def direct_send(self, text, user_ids=(), thread_ids=(), **kwargs):
                raise KeyboardInterrupt

        client = InterruptSend()
        with patch("ai_chat.time.sleep", side_effect=KeyboardInterrupt):
            ai_chat.chat_loop(client, _cfg())


    def test_whitelist_menu_persists_to_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"whitelist": []}
            target = Path(tmp) / "config.json"
            with patch("config.CONFIG_PATH", target), patch(
                "ai_chat.prompt", side_effect=["1", "alexnova", "3"]
            ):
                ai_chat._whitelist_menu(cfg, persist=True)
            saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertIn("alexnova", cfg["whitelist"])
        self.assertIn("alexnova", saved["whitelist"])

    def test_whitelist_menu_skips_write_in_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"whitelist": []}
            target = Path(tmp) / "config.json"
            with patch("config.CONFIG_PATH", target), patch(
                "ai_chat.prompt", side_effect=["1", "alexnova", "3"]
            ):
                ai_chat._whitelist_menu(cfg, persist=False)
            self.assertFalse(target.exists())
        self.assertIn("alexnova", cfg["whitelist"])

    def test_whitelist_menu_remove_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"whitelist": ["alexnova", "brianna_k"]}
            target = Path(tmp) / "config.json"
            with patch("config.CONFIG_PATH", target), patch(
                "ai_chat.prompt", side_effect=["2", "alexnova", "3"]
            ):
                ai_chat._whitelist_menu(cfg, persist=True)
            saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(cfg["whitelist"], ["brianna_k"])
        self.assertEqual(saved["whitelist"], ["brianna_k"])

    def test_aborted_error_returns_to_menu_not_traceback(self):
        import main as main_mod

        with patch("main.show_banner"), patch(
            "main.config_mod.load_config", return_value={"session_path": "/tmp/x.json"}
        ), patch("main.config_mod.first_run", return_value=False), patch(
            "main.ensure_deps", return_value=True
        ), patch("main.client_factory", return_value=object()), patch(
            "actions.login", return_value=object()
        ), patch(
            "main.main_menu", side_effect=actions.AbortedError("cancelled")
        ):
            main_mod.main()

    def test_main_catches_keyboard_interrupt_at_menu(self):
        import main as main_mod

        with patch("main.show_banner"), patch(
            "main.config_mod.load_config", return_value={"session_path": "/tmp/x.json"}
        ), patch("main.config_mod.first_run", return_value=False), patch(
            "main.ensure_deps", return_value=True
        ), patch("main.client_factory", return_value=object()), patch(
            "actions.login", return_value=object()
        ), patch("main.main_menu", side_effect=KeyboardInterrupt):
            main_mod.main()


class ToolTests(unittest.TestCase):
    def test_non_mutual_uses_str_pks(self):
        client = FakeClient()
        following = list(client.user_following(client.user_id).values())
        followers = client.user_followers(client.user_id)
        follower_ids = {str(k) for k in followers.keys()}
        targets = [u for u in following if str(u.pk) not in follower_ids]
        self.assertEqual({str(u.pk) for u in targets}, {"3", "6", "9", "12", "15"})

    def test_leave_chat_detects_groups_via_is_group(self):
        client = FakeClient()
        groups = leave_chat._list_groups(client)
        ids = {str(g.id) for g in groups}
        self.assertEqual(ids, {"1001", "1003", "1004"})

    def test_fake_client_marks_itself(self):
        self.assertTrue(FakeClient.is_fake)
        self.assertTrue(FakeClient().is_fake)


class UiTests(unittest.TestCase):
    def test_clip_keeps_ansi_codes_intact(self):
        from ui import _clip

        text = "ab\x1b[31mcd\x1b[0m ef"
        self.assertEqual(_clip(text, 4), "ab\x1b[31mc…")
        self.assertEqual(len(_clip(text, 4).replace("\x1b[31m", "").replace("\x1b[0m", "")), 4)

    def test_clip_noop_when_short_enough(self):
        from ui import _clip

        self.assertEqual(_clip("hello", 10), "hello")
        self.assertEqual(_clip("", 0), "")

    def test_box_aligns_and_clips_at_narrow_width(self):
        import contextlib
        import io
        from ui import _clip, _visible_len, box

        with patch("ui._terminal_width", return_value=12):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                box("test menu", ["1  some long option label here", "2  back"])
        lines = [l for l in buf.getvalue().splitlines() if l]
        widths = {_visible_len(l) for l in lines}
        self.assertEqual(widths, {14}, f"all box rows must share one width, got {widths}")
        self.assertTrue(any("…" in l for l in lines), "long lines must be clipped")


if __name__ == "__main__":
    unittest.main()