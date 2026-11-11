"""Run the Windows logger health check without creating a console window."""
import logging
import os
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    log_directory = root / "logger" / "data"
    log_directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=log_directory / "watchdog.log", encoding="utf-8",
                        level=logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")
    powershell = (Path(os.environ["SystemRoot"]) / "System32" /
                  "WindowsPowerShell" / "v1.0" / "powershell.exe")
    command = [str(powershell), "-NoProfile", "-NonInteractive",
               "-ExecutionPolicy", "Bypass", "-File", str(root / "check_logger.ps1")]
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=45)
    except (OSError, subprocess.SubprocessError):
        logging.exception("Logger watchdog could not complete its health check")
        return 1
    if result.returncode:
        logging.error("Logger health check failed (%s): %s", result.returncode,
                      result.stderr.strip() or result.stdout.strip())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
