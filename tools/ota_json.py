#!/usr/bin/env python3
# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
"""Write the Evolution X Updater entry for a built OTA package.

Updater accepts an entry only when every field below is present and timestamp is
newer than the device's ro.build.date.utc, so timestamp comes from the package's own
OTA metadata (post-timestamp) rather than from the file name or upload time.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile


def metadata(package):
    with zipfile.ZipFile(package) as archive:
        text = archive.read("META-INF/com/android/metadata").decode()
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def entry(package, url, maintainer=""):
    package = Path(package)
    meta = metadata(package)
    version = re.match(r"EvolutionX-([0-9.]+)-", package.name)
    if not version or meta.get("ota-type") != "AB":
        raise ValueError(f"Not an Evolution X A/B OTA package: {package.name}")
    md5 = hashlib.md5()
    with package.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(chunk)
    return {
        "filename": package.name,
        "download": url,
        "timestamp": int(meta["post-timestamp"]),
        "md5": md5.hexdigest(),
        "size": package.stat().st_size,
        "version": version.group(1),
        "maintainer": maintainer,
        "forum": "",
        "firmware": "",
        "paypal": "",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--url", required=True, help="final download URL of the package")
    parser.add_argument("--maintainer", default="")
    args = parser.parse_args(argv)
    try:
        print(json.dumps({"response": [entry(args.package, args.url, args.maintainer)]}, indent=2))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
