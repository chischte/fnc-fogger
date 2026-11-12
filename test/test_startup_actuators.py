"""Exercise real startup timing, output drivers, tach counting and OTA shutdown."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StartupActuatorTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32" and shutil.which("clang++"),
                         "Requires Windows with Clang and LLD")
    def test_boot_pulses_rpm_and_maintenance(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "startup_actuators.exe"
            command = [
                "clang++", "-std=c++17", "-O1", "-ffreestanding", "-fno-exceptions",
                "-fno-rtti", "-fno-stack-protector", "-fuse-ld=lld", "-nostdlib",
                "-DCONFIG_IDF_TARGET_ESP32C3", "-DARDUINO_ARCH_ESP32",
                "-Itest/actuator_fakes", "-Itest/control_fakes", "-Iinclude", "test/test_startup_actuators.cpp",
                "src/firmware/automatic_control.cpp", "src/firmware/pi_controller.cpp", "src/firmware/startup_test.cpp", "src/firmware/manual_control.cpp", "src/esp32/startup_actuators.cpp",
                "-Wl,/entry:main,/subsystem:console", "-o", str(executable),
            ]
            compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], timeout=10)
            self.assertEqual(result.returncode, 0, f"Startup test failed at C++ line {result.returncode}")
