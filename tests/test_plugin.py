import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import plugin


class PluginTests(unittest.TestCase):
    def test_checkout_preserves_foreground_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "src"
            source.mkdir()
            pane = {"cwd": directory, "foreground_cwd": str(source),
                    "workspace_id": "w1", "pane_id": "w1:p2"}
            with patch.dict(os.environ, {"HERDR_PANE_ID": "w1:p2", "HERDR_WORKSPACE_ID": "w1"}), \
                 patch.object(plugin, "run", return_value=json.dumps({"result": {"pane": pane}})) as run, \
                 patch.object(plugin.subprocess, "run", return_value=Mock(returncode=0, stdout=directory)) as git:
                selected, workspace, pane_id = plugin.checkout("/herdr")
            self.assertEqual((selected, workspace, pane_id), (source.resolve(), "w1", "w1:p2"))
            run.assert_called_once_with(["/herdr", "pane", "get", "w1:p2"])
            git.assert_not_called()

    def test_missing_directory_does_not_open_plugin_source(self):
        with patch.dict(os.environ, {"HERDR_PANE_ID": "p1"}, clear=True), \
             patch.object(plugin, "run", return_value=json.dumps({"result": {"pane": {}}})):
            with self.assertRaisesRegex(RuntimeError, "directory"):
                plugin.checkout("herdr")

    def test_other_workspace_is_rejected(self):
        with patch.dict(os.environ, {"HERDR_WORKSPACE_ID": "w1"}), \
             patch.object(plugin, "run", return_value=json.dumps({"result": {"pane": {"workspace_id": "w2"}}})):
            with self.assertRaisesRegex(RuntimeError, "workspace"):
                plugin.checkout("herdr")

    def test_only_own_browser_tab_matches(self):
        state = {"tab_id": 5, "workspace": "w1", "url": "http://127.0.0.1:7777/"}
        own = {"id": 5, "workspace": "w1", "location": state["url"]}
        self.assertEqual(plugin.matching_tab([own], state), own)
        self.assertIsNone(plugin.matching_tab([{**own, "workspace": "w2"}], state))
        self.assertIsNone(plugin.matching_tab([{**own, "location": "https://example.com"}], state))
        self.assertIsNone(plugin.matching_tab([{**own, "id": 6}], state))
        self.assertIsNotNone(plugin.matching_tab([{**own, "location": state["url"] + "?file=README.md"}], state))

    def test_gui_binary_does_not_resolve_case_insensitive_herdr_cli(self):
        with patch.dict(os.environ, {"HERDR_PLUGIN_STATE_DIR": "/unused"}, clear=True), \
             patch.object(plugin.sys, "argv", ["plugin.py", "close"]), \
             patch.object(plugin, "executable", return_value="/gui") as executable, \
             patch.object(plugin.Path, "mkdir"), patch.object(plugin, "close_px0"):
            plugin.main()
        executable.assert_called_once_with("HERDR_GPUI_BIN", "herdr-gpui",
                                           "/Applications/Herdr.app/Contents/MacOS/Herdr")

    def test_open_failure_stops_server(self):
        with tempfile.TemporaryDirectory() as directory:
            process = Mock()
            with patch.object(plugin, "checkout", return_value=(Path(directory), "w1", "p1")), \
                 patch.object(plugin, "executable", return_value="px0"), \
                 patch.object(plugin, "start_server", return_value=(process, "http://127.0.0.1:7777/")), \
                 patch.object(plugin, "run", side_effect=[json.dumps({"windows": [{"id": 1, "workspace": "w1"}]}), RuntimeError("browser failed")]), \
                 patch.object(plugin, "stop_server") as stop:
                with self.assertRaisesRegex(RuntimeError, "browser failed"):
                    plugin.open_px0("herdr", "gui", Path(directory))
            stop.assert_called_once_with(process)

    def test_startup_failure_stops_server(self):
        with tempfile.TemporaryDirectory() as directory:
            process = Mock()
            process.poll.return_value = 1
            with patch.object(plugin.subprocess, "Popen", return_value=process), \
                 patch.object(plugin, "stop_server") as stop:
                with self.assertRaisesRegex(RuntimeError, "exited"):
                    plugin.start_server("px0", Path(directory), Path(directory) / "log")
            stop.assert_called_once_with(process)

    def test_startup_timeout_stops_child(self):
        with tempfile.TemporaryDirectory() as directory:
            process = Mock()
            process.poll.return_value = None
            with patch.object(plugin.subprocess, "Popen", return_value=process), \
                 patch.object(plugin, "stop_server") as stop:
                with self.assertRaisesRegex(RuntimeError, "ready"):
                    plugin.start_server("px0", Path(directory), Path(directory) / "log", timeout=0)
            stop.assert_called_once_with(process)

    def test_stop_escalates_if_server_will_not_exit(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("px0", 5), 0]
        plugin.stop_server(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()

    def test_close_leaves_other_workspace_tabs_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {"workspace": "w2", "tab_id": 1, "window": 2, "url": "http://127.0.0.1:1/"}
            (Path(directory) / "other.json").write_text(json.dumps(state))
            with patch.dict(os.environ, {"HERDR_WORKSPACE_ID": "w1"}), patch.object(plugin, "run") as run:
                plugin.close_px0("Herdr", Path(directory))
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
