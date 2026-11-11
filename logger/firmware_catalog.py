"""Find compatible newer stable firmware among locally prepared images."""
import re
from pathlib import Path

from .firmware_update import read_image


def release_version(value):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-esp32c3|-esp32s3)?", value)
    return tuple(map(int, match.groups())) if match else None


def available_versions(directory):
    directory = Path(directory)
    newest = {}
    paths = [*directory.glob("*.bin"), *directory.glob("legacy/*/*.bin")]
    for path in paths:
        try:
            image = read_image(path)
        except (OSError, ValueError):
            continue
        version = release_version(image.version)
        if version is not None:
            newest[image.profile] = max(newest.get(image.profile, version), version)
    return newest


def has_newer_firmware(device, versions):
    current = release_version(device.firmware)
    profile = device.hardware_profile
    if not profile and device.firmware.endswith("-esp32s3"):
        profile = "esp32s3"
    newest = versions.get(profile)
    return current is not None and newest is not None and newest > current
