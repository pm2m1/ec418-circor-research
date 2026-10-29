#!/usr/bin/env python3
"""Retrieve the exact WEKA 3.9.7 runtime JARs used in the study.

Only uses Python's standard library. Pins the PyPI release source archive and
its SHA-256, then verifies every extracted JAR's SHA-256 before writing.
Usage: python scripts/install_weka_jars.py [--verify]
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import Request, urlopen

VERSION = "0.3.3"
ARCHIVE_NAME = f"python_weka_wrapper3-{VERSION}.tar.gz"
ARCHIVE_SHA256 = "5b7208b99116cb882cf24f1d72e3e1380d29f0859bc419872b8a0e0b5e90883f"
JARS = {
    "weka.jar": "e60ffffbebbb49d1805a2b77075c869706802af93b8e876a8e0ac9a435698cc3",
    "mtj.jar": "641f74e1fe54886183076d0dc9dd8589422148f1fd4f054fe62ee268e875f315",
    "core.jar": "5ffaddee0a3f8d09a56064aa05feb95837ddad9d42d9dcc37479c66e869aa139",
    "arpack_combined.jar": "8d55d2bc18af3d5dfc8106d79b659cb7c7c76307d6d1021401dcb45f40f40575",
}
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "tools"


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def check_files():
    missing = []
    for name, expected in JARS.items():
        file = DEST / name
        if not file.is_file():
            missing.append(name)
            print(f"MISSING {name}")
            continue
        got = hashlib.sha256(file.read_bytes()).hexdigest()
        if got != expected:
            raise SystemExit(f"SHA256 MISMATCH: {name}: {got} != {expected}; refusing to overwrite")
        print(f"OK {name} SHA256={got}")
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify existing JARs without downloading")
    args = parser.parse_args()
    missing = check_files()
    if args.verify:
        if missing:
            raise SystemExit("Missing runtime JARs; run without --verify to install")
        return
    if not missing:
        print("All four verified runtime JARs are present; nothing to install.")
        return
    print("Downloading pinned python-weka-wrapper3 0.3.3 source archive from PyPI...")
    metadata_url = f"https://pypi.org/pypi/python-weka-wrapper3/{VERSION}/json"
    with urlopen(Request(metadata_url, headers={"User-Agent": "EC418-repro/1.0"}), timeout=30) as response:
        metadata = json.load(response)
    matches = [e for e in metadata.get("urls", []) if e.get("filename") == ARCHIVE_NAME]
    if len(matches) != 1:
        raise SystemExit("Pinned source archive not found in PyPI metadata")
    entry = matches[0]
    if entry.get("digests", {}).get("sha256") != ARCHIVE_SHA256:
        raise SystemExit("Unexpected PyPI archive checksum; refusing download")
    with urlopen(Request(entry["url"], headers={"User-Agent": "EC418-repro/1.0"}), timeout=120) as response:
        archive = response.read()
    if sha256(archive) != ARCHIVE_SHA256:
        raise SystemExit("Downloaded archive checksum mismatch")
    payloads = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            for name in missing:
                if member.name.endswith("/python/weka/lib/" + name):
                    if name in payloads:
                        raise SystemExit(f"Duplicate JAR entry: {name}")
                    payload = tar.extractfile(member).read()
                    if sha256(payload) != JARS[name]:
                        raise SystemExit(f"Embedded JAR checksum mismatch: {name}")
                    payloads[name] = payload
    if sorted(payloads) != sorted(missing):
        raise SystemExit(f"Missing expected source-archive JARs: {set(missing) - set(payloads)}")
    DEST.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (DEST / name).write_bytes(payload)
        print(f"Installed verified tools/{name}")
    if check_files():
        raise SystemExit("Verification incomplete")
    print("WEKA runtime ready. Check with: java -cp 'tools/*' weka.core.Version")


if __name__ == "__main__":
    main()
