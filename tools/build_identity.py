"""Give each firmware build a reproducible source/configuration fingerprint."""
import hashlib
import json
import re
from pathlib import Path

Import("env")

root = Path(env.subst("$PROJECT_DIR"))
digest = hashlib.sha256()
paths = [root / "platformio.ini", root / "tools/build_identity.py", *root.glob("partitions_*.csv")]
for directory in ("src", "include"):
    paths.extend((root / directory).rglob("*"))
for path in sorted(path for path in paths if path.is_file()):
    digest.update(path.relative_to(root).as_posix().encode())
    digest.update(path.read_bytes())
digest.update(env.subst("$PIOENV").encode())
env.Append(CPPDEFINES=[("FNC_BUILD_ID", '\\"' + digest.hexdigest()[:12] + '\\"')])


def write_manifest(source, target, env):
    binary = Path(env.subst("$BUILD_DIR")) / "firmware.bin"
    data = binary.read_bytes()
    matches = set(re.findall(rb"FNC_FW\|([a-z0-9_]+)\|([a-zA-Z0-9.-]+)\|([a-f0-9]{12})\|END", data))
    if len(matches) != 1:
        raise ValueError("Firmware build metadata is missing or ambiguous")
    profile, version, build_id = (part.decode("ascii") for part in matches.pop())
    manifest = dict(hardware_profile=profile, firmware=version, build_id=build_id,
                    sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data), file=binary.name)
    binary.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", write_manifest)
