"""Verify incremental scanning, device presence and bus errors without hardware."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class I2cDiagnosticsTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32" and shutil.which("clang++"),
                         "Requires Windows with Clang and LLD")
    def test_incremental_scan_and_rescan(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "i2c_diagnostics.exe"
            command = [
                "clang++", "-std=c++17", "-ffreestanding", "-fno-exceptions",
                "-fno-rtti", "-fno-stack-protector", "-fuse-ld=lld", "-nostdlib",
                "-Itest/i2c_fakes", "-Itest/fakes", "-Iinclude", "test/test_i2c_diagnostics.cpp",
                "src/esp32/i2c_diagnostics.cpp", "-Wl,/entry:main,/subsystem:console", "-o", str(executable),
            ]
            compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], timeout=10)
            self.assertEqual(result.returncode, 0, f"I2C scan failed at C++ line {result.returncode}")
