"""Exercise the firmware's real persistence logic against a fake NVS backend."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ControlSettingsTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32" and shutil.which("clang++"),
                         "Requires Windows with Clang and LLD")
    def test_restore_validation_and_failed_nvs_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "control_settings.exe"
            command = [
                "clang++", "-std=c++17", "-O1", "-ffreestanding", "-fno-exceptions",
                "-fno-rtti", "-fno-stack-protector", "-fuse-ld=lld", "-nostdlib",
                "-DARDUINO_ARCH_ESP32", "-Itest/control_fakes", "-Iinclude",
                "test/test_control_settings.cpp", "src/firmware/control_settings_store.cpp", "src/esp32/cyclic_mist_store.cpp", "src/esp32/pi_memory.cpp", "src/esp32/humidity_calibration_store.cpp",
                "-Wl,/entry:main,/subsystem:console", "-o", str(executable),
            ]
            compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], timeout=10)
            self.assertEqual(result.returncode, 0,
                             f"Control settings check failed at C++ line {result.returncode}")
