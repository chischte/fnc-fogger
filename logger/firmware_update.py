"""Validate one firmware image and update one explicitly identified lance."""
import argparse
import hashlib
import re
import threading
import time
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .logger import fetch_json
from .lance_registry import Lance, LanceRegistry

PROFILE_CHIPS = {"esp32s3": 9, "esp32c3_supermini": 5}
METADATA_PATTERN = rb"FNC_FW\|([a-z0-9_]+)\|([a-zA-Z0-9.-]+)\|([a-f0-9]{12})\|END"
REBOOT_TIMEOUT_SECONDS = 90
REBOOT_POLL_SECONDS = 2
UPLOAD_TIMEOUT_SECONDS = 300
ESP_IMAGE_HEADER_BYTES = 24
ESP_IMAGE_MAGIC = 0xE9
ESP_IMAGE_CHIP_ID_OFFSET = 12
ESP_IMAGE_CHIP_ID_BYTES = 2


@dataclass(frozen=True)
class FirmwareImage:
    path: Path
    profile: str
    version: str
    build_id: str
    sha256: str
    data: bytes


def read_image(path):
    path = Path(path)
    data = path.read_bytes()
    matches = set(re.findall(METADATA_PATTERN, data))
    if len(matches) != 1 or len(data) < ESP_IMAGE_HEADER_BYTES or data[0] != ESP_IMAGE_MAGIC:
        raise ValueError("Select a prepared FNC firmware.bin with unique build metadata.")
    profile, version, build_id = (part.decode("ascii") for part in matches.pop())
    chip_end = ESP_IMAGE_CHIP_ID_OFFSET + ESP_IMAGE_CHIP_ID_BYTES
    chip = int.from_bytes(data[ESP_IMAGE_CHIP_ID_OFFSET:chip_end], "little")
    if profile not in PROFILE_CHIPS or chip != PROFILE_CHIPS[profile]:
        raise ValueError("Image chip and hardware profile do not match.")
    return FirmwareImage(path, profile, version, build_id, hashlib.sha256(data).hexdigest(), data)


def check_target(lance, image):
    status = fetch_json(lance.url + "/api/current")
    device_id = status.get("device_id")
    if device_id:
        if device_id != lance.device_id:
            raise ValueError("Target device ID changed. Refresh device selection.")
        profile = status.get("hardware_profile")
    else:
        # Bootstrap the deployed S3 release, which predates identity in the API.
        expected_host = f"fnc-fogger-{lance.device_id[-6:]}.local"
        if lance.hostname != expected_host or not status.get("firmware", "").endswith("-esp32s3"):
            raise ValueError("Legacy firmware requires its device-specific mDNS name.")
        profile = "esp32s3"
    if image.profile != profile:
        raise ValueError(f"Firmware for {image.profile} cannot be installed on {profile}.")
    return status


def install(lance, image, report, stop):
    before = check_target(lance, image)
    if stop.is_set():
        raise RuntimeError("Update cancelled before upload.")
    report("uploading", before)
    _upload_image(lance, image)
    report("awaiting_restart", before)
    status = _wait_for_restart(lance, image, before, stop)
    report("verified", status)
    return status


def _upload_image(lance, image):
    boundary = "fnc-" + uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"firmware\"; "
            'filename="firmware.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
    body += image.data + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(lance.url + "/update", data=body, method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=UPLOAD_TIMEOUT_SECONDS) as response:
        response.read()


def _wait_for_restart(lance, image, before, stop):
    deadline = time.monotonic() + REBOOT_TIMEOUT_SECONDS
    previous_boot = before.get("measurement", {}).get("boot_id")
    while time.monotonic() < deadline and not stop.wait(REBOOT_POLL_SECONDS):
        try:
            status = fetch_json(lance.url + "/api/current")
        except (OSError, ValueError):
            continue
        if status.get("device_id") != lance.device_id:
            raise RuntimeError("Device identity could not be confirmed after upload.")
        new_boot = status.get("measurement", {}).get("boot_id")
        if (status.get("firmware") == image.version and status.get("build_id") == image.build_id
                and status.get("hardware_profile") == image.profile
                and new_boot is not None and new_boot != previous_boot):
            return status
    raise RuntimeError("Update not confirmed: no matching firmware and new boot within 90 seconds. Refresh before retrying.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    address = urlsplit(args.url)
    if address.scheme != "http" or not address.hostname or address.path not in ("", "/"):
        parser.error("Use a device base URL: http://hostname[:port]")
    if not re.fullmatch(r"[0-9a-f]{12}", args.device_id):
        parser.error("Device ID must contain 12 lowercase hexadecimal characters")
    lance = Lance(args.device_id, address.hostname, address.port or 80)
    image = read_image(args.file)
    status = check_target(lance, image)
    print(f"Target: {lance.device_id} at {lance.url}\nHardware: {image.profile}\n"
          f"Firmware: {status.get('firmware')} -> {image.version} ({image.build_id})\nSHA256: {image.sha256}")
    if not args.yes and input("Install on this device? [y/N] ").lower() != "y":
        return
    registry = LanceRegistry(Path(__file__).parent / "data")
    registry.remember(lance, status=status)

    def report(phase, payload):
        registry.record_update(lance.device_id, image, phase)
        print(phase)

    try:
        result = install(lance, image, report, threading.Event())
        registry.remember(lance, status=result)
    except Exception as error:
        registry.record_update(lance.device_id, image, "unconfirmed", str(error))
        raise


if __name__ == "__main__":
    main()
