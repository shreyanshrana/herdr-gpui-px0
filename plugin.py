import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def run(argv):
    return subprocess.check_output(argv, text=True)


def executable(variable, name, fallback):
    value = os.environ.get(variable) or shutil.which(name) or fallback
    if not value or not os.access(value, os.X_OK):
        raise RuntimeError(f"Cannot find {name}; install it or set {variable}.")
    return value


def checkout(cli):
    pane_id = os.environ.get("HERDR_PANE_ID")
    args = ["pane", "get", pane_id] if pane_id else ["pane", "current"]
    pane = json.loads(run([cli, *args]))["result"]["pane"]
    workspace = os.environ.get("HERDR_WORKSPACE_ID")
    if workspace and pane.get("workspace_id") != workspace:
        raise RuntimeError("The terminal does not belong to the invoking workspace.")
    cwd = pane.get("foreground_cwd") or pane.get("cwd")
    if not cwd:
        raise RuntimeError("Cannot identify the terminal's directory.")
    directory = Path(cwd).resolve(strict=True)
    return directory, pane["workspace_id"], pane["pane_id"]


def ready(url):
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def start_server(px0, directory, log_path, timeout=20):
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [px0, "-no-open", "-no-update", "-no-telemetry", "-host", "127.0.0.1",
             "-port", "0", str(directory)],
            cwd=directory, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        )
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"px0 exited during startup. See {log_path}")
            match = re.search(r"http://(?:127\.0\.0\.1|localhost):\d+", log_path.read_text())
            if match and ready(match.group()):
                return process, match.group() + "/"
            time.sleep(0.1)
        raise RuntimeError(f"px0 did not become ready. See {log_path}")
    except BaseException:
        stop_server(process)
        raise


def stop_server(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def tabs(gui, window):
    return json.loads(run([gui, "browser", "list", "--window", str(window), "--json"]))


def matching_tab(items, state):
    origin = urllib.parse.urlsplit(state["url"])
    return next((tab for tab in items
                 if tab["id"] == state["tab_id"]
                 and tab.get("workspace") == state["workspace"]
                 and urllib.parse.urlsplit(tab.get("location", ""))[:2] == origin[:2]), None)


def open_px0(cli, gui, state_dir):
    directory, workspace, pane = checkout(cli)
    key = hashlib.sha256(f"{workspace}\0{pane}\0{directory}".encode()).hexdigest()[:20]
    state_path = state_dir / f"{key}.json"
    with (state_dir / f"{key}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # The first invocation owns the server until its browser tab closes.
            for _ in range(220):
                if state_path.exists():
                    state = json.loads(state_path.read_text())
                    if matching_tab(tabs(gui, state["window"]), state):
                        run([gui, "tab", "focus", str(state["tab_id"]),
                             "--window", str(state["window"])])
                        return
                time.sleep(0.1)
            raise RuntimeError("px0 is already starting or closing; try again shortly.")
        state_path.unlink(missing_ok=True)
        px0 = executable("PX0_BIN", "px0", str(Path.home() / ".local/bin/px0"))
        windows = json.loads(run([gui, "status", "--json"]))["windows"]
        window = next((w["id"] for w in windows if w.get("workspace") == workspace), None)
        if window is None:
            raise RuntimeError("No Herdr GPUI window shows this workspace.")
        process, url = start_server(px0, directory, state_dir / f"{key}.log")
        try:
            run([gui, "browser", "open", url, "--beside", "--workspace", workspace])
            tab = next((t for t in tabs(gui, window)
                        if t.get("location") == url and t.get("workspace") == workspace), None)
            if tab is None:
                raise RuntimeError("Cannot find the px0 browser tab after opening it.")
            state = {"workspace": workspace, "pane": pane, "directory": str(directory),
                     "url": url, "tab_id": tab["id"], "window": window}
            temporary = state_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state))
            temporary.replace(state_path)
            print(f"px0 opened for {directory}", flush=True)
            while process.poll() is None:
                result = subprocess.run(
                    [gui, "wait", "tab-closed", str(tab["id"]), "--window", str(window),
                     "--timeout", "2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                if result.returncode in (0, 3, 5):
                    break
                if result.returncode != 4:
                    time.sleep(1)
        finally:
            stop_server(process)
            state_path.unlink(missing_ok=True)


def close_px0(gui, state_dir):
    workspace = os.environ.get("HERDR_WORKSPACE_ID")
    if not workspace:
        raise RuntimeError("Close px0 must be invoked from a workspace.")
    for path in state_dir.glob("*.json"):
        try:
            state = json.loads(path.read_text())
        except FileNotFoundError:
            continue
        if state["workspace"] == workspace and matching_tab(tabs(gui, state["window"]), state):
            run([gui, "browser", "close", str(state["tab_id"]),
                 "--window", str(state["window"])])


def main():
    if sys.argv[1:] not in (["open"], ["close"]):
        raise RuntimeError("Usage: python3 plugin.py open|close")
    gui = executable("HERDR_GPUI_BIN", "herdr-gpui", "/Applications/Herdr.app/Contents/MacOS/Herdr")
    state_dir = Path(os.environ["HERDR_PLUGIN_STATE_DIR"])
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if sys.argv[1] == "close":
        close_px0(gui, state_dir)
    else:
        cli = executable("HERDR_BIN_PATH", "herdr", str(Path.home() / ".local/bin/herdr"))
        open_px0(cli, gui, state_dir)


def interrupted(signum, frame):
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        sys.exit(f"herdr-gpui-px0: {error}")
