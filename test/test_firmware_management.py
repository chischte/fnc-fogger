"""Exercise identity checks, registry migration and restart confirmation without hardware."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from logger.firmware_update import check_target, install, read_image
from logger.lance_registry import Lance, LanceRegistry


class FirmwareManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lance = Lance("112233445566", "fnc-fogger-445566.local", 80)
        header = bytearray(24)
        header[0] = 0xE9
        header[12] = 5
        self.path = self.root / "firmware.bin"
        self.path.write_bytes(header + b"FNC_FW|esp32c3_supermini|3.2.0-esp32c3|0123456789ab|END")
        self.image = read_image(self.path)
        self.before = dict(device_id=self.lance.device_id, hardware_profile=self.image.profile,
                           firmware="3.1.0", build_id="previous", measurement={"boot_id": 1})

    def tearDown(self):
        self.temp.cleanup()

    def test_reject_chip_and_profile_mismatch(self):
        data = bytearray(self.path.read_bytes())
        data[12] = 9
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "chip"):
            read_image(self.path)

    def test_reject_wrong_device_and_profile_before_upload(self):
        for changed in ({"device_id": "aabbccddeeff"}, {"hardware_profile": "esp32s3"}):
            with self.subTest(changed=changed), patch("logger.firmware_update.fetch_json",
                                                      return_value=self.before | changed):
                with self.assertRaises(ValueError):
                    check_target(self.lance, self.image)

    def test_legacy_bootstrap_rejects_ip_address_and_c3_image(self):
        legacy = {"firmware": "3.1.4-esp32s3"}
        with patch("logger.firmware_update.fetch_json", return_value=legacy):
            with self.assertRaises(ValueError):
                check_target(Lance(self.lance.device_id, "192.168.1.2", 80), self.image)
            with self.assertRaises(ValueError):
                check_target(self.lance, self.image)

    def test_success_requires_matching_firmware_and_new_boot(self):
        after = self.before | dict(firmware=self.image.version, build_id=self.image.build_id,
                                   measurement={"boot_id": 2})
        unchanged_boot = after | {"measurement": {"boot_id": 1}}
        stop = Mock()
        stop.is_set.return_value = False
        stop.wait.return_value = False
        report = Mock()
        with patch("logger.firmware_update.fetch_json", side_effect=[self.before, unchanged_boot, after]), \
                patch("logger.firmware_update.urllib.request.urlopen") as upload:
            self.assertEqual(install(self.lance, self.image, report, stop), after)
        self.assertEqual([call.args[0] for call in report.call_args_list],
                         ["uploading", "awaiting_restart", "verified"])
        self.assertEqual(upload.call_args.args[0].full_url, self.lance.url + "/update")

    def test_missing_restart_remains_unconfirmed(self):
        stop = Mock()
        stop.is_set.return_value = False
        stop.wait.return_value = True
        with patch("logger.firmware_update.fetch_json", return_value=self.before), \
                patch("logger.firmware_update.urllib.request.urlopen"):
            with self.assertRaisesRegex(RuntimeError, "not confirmed"):
                install(self.lance, self.image, Mock(), stop)

    def test_registry_migrates_existing_labels_and_remembers_offline_firmware(self):
        with closing(sqlite3.connect(self.root / "lances.db")) as db, db:
            db.execute("""CREATE TABLE lances(device_id TEXT PRIMARY KEY, hostname TEXT NOT NULL,
                port INTEGER NOT NULL, name TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '',
                database_name TEXT NOT NULL UNIQUE)""")
            db.execute("INSERT INTO lances VALUES(?,?,?,?,?,?)",
                       (self.lance.device_id, self.lance.hostname, 80, "Lance 02", "Lab", "old.db"))
        registry = LanceRegistry(self.root)
        remembered = registry.remember(self.lance, status=self.before)
        registry.record_update(self.lance.device_id, self.image, "verified")
        restarted = LanceRegistry(self.root).list()[0]
        self.assertEqual((restarted.name, restarted.database_name), ("Lance 02", "old.db"))
        self.assertEqual(restarted.firmware, self.before["firmware"])
        self.assertEqual(restarted.last_seen, remembered.last_seen)
        with closing(sqlite3.connect(registry.path)) as db:
            self.assertEqual(db.execute("SELECT phase,sha256 FROM firmware_updates").fetchone(),
                             ("verified", self.image.sha256))
