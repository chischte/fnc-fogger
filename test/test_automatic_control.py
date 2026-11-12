"""Run real portable PI logic and hardware arbitration with fake GPIOs."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AutomaticControlTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32" and shutil.which("clang++"),
                         "Requires Windows with Clang and LLD")
    def test_limits_interlocks_faults_and_fresh_samples(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "automatic.exe"
            result = subprocess.run([
                "clang++", "-std=c++17", "-O1", "-ffreestanding", "-fno-exceptions",
                "-fno-rtti", "-fno-stack-protector", "-fuse-ld=lld", "-nostdlib",
                "-DCONFIG_IDF_TARGET_ESP32C3", "-DARDUINO_ARCH_ESP32",
                "-Itest/actuator_fakes", "-Itest/control_fakes", "-Iinclude",
                "test/test_automatic_control.cpp", "src/firmware/automatic_control.cpp",
                "src/firmware/pi_controller.cpp", "src/firmware/startup_test.cpp",
                "src/firmware/manual_control.cpp", "src/esp32/startup_actuators.cpp",
                "-Wl,/entry:main,/subsystem:console", "-o", str(executable)],
                cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable)], timeout=10)
            self.assertEqual(result.returncode, 0, f"C++ check failed at line {result.returncode}")
