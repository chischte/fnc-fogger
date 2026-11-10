"""Start the independent logger without tying its lifetime to the viewer."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

TASK_NAME = "fnc-fogger-logger"


def healthy(directory, max_age=45):
    try:
        status = json.loads((Path(directory) / "background-status.json").read_text(encoding="utf-8"))
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(status["updated_at"])).total_seconds()
        return 0 <= age < max_age
    except (OSError, ValueError, KeyError, TypeError):
        return False


def ensure_background_logger(directory):
    if healthy(directory):
        return
    root = Path(__file__).resolve().parents[1]
    if os.name == "nt":
        command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                   "-Command", f"$ErrorActionPreference='Stop'; Start-ScheduledTask -TaskName '{TASK_NAME}'"]
        try:
            result = subprocess.run(command, creationflags=subprocess.CREATE_NO_WINDOW,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            if result.returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            pass
    executable = Path(sys.executable)
    if os.name == "nt" and executable.with_name("pythonw.exe").exists():
        executable = executable.with_name("pythonw.exe")
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    subprocess.Popen([str(executable), "-m", "logger.background", "--directory", str(Path(directory).resolve())],
                     cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=flags, start_new_session=os.name != "nt")
