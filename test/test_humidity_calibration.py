import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class HumidityCalibrationTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32" and shutil.which("clang++"),
                         "Requires Windows with Clang and LLD")
    def test_reference_replacement_timer_and_storage_failure(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "calibration.exe"
            result = subprocess.run([
                "clang++", "-std=c++17", "-O1", "-ffreestanding", "-fno-exceptions",
                "-fno-rtti", "-fno-stack-protector", "-fuse-ld=lld", "-nostdlib",
                "-Itest/actuator_fakes", "-Itest/control_fakes", "-Iinclude",
                "test/test_humidity_calibration.cpp", "src/firmware/humidity_calibration.cpp",
                "-Wl,/entry:main,/subsystem:console", "-o", str(executable)],
                cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable)], timeout=10)
            self.assertEqual(result.returncode, 0, f"C++ check failed at line {result.returncode}")
