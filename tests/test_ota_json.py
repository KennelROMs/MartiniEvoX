# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
"""The Updater entry carries the package's own OTA timestamp and every required field."""

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


CONTROL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ota_json", CONTROL / "tools/ota_json.py")
ota_json = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ota_json)

# Fields Evolution X Updater reads with getString/getLong; a missing one drops the entry.
REQUIRED = {"timestamp", "filename", "md5", "size", "download", "version",
            "maintainer", "forum", "firmware", "paypal"}


class OtaJsonTests(unittest.TestCase):
    def package(self, directory, name, ota_type="AB"):
        path = Path(directory) / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("META-INF/com/android/metadata",
                             f"ota-type={ota_type}\npost-timestamp=1790883857\npre-device=MT2111_IND\n")
            archive.writestr("payload.bin", b"payload")
        return path

    def test_entry_uses_package_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.package(directory, "EvolutionX-17.0-20261001-martini-12.2-Unofficial.zip")
            entry = ota_json.entry(path, "https://example.invalid/rom.zip")
            self.assertEqual(set(entry), REQUIRED)
            self.assertEqual(entry["timestamp"], 1790883857)
            self.assertEqual(entry["version"], "17.0")
            self.assertEqual(entry["md5"], hashlib.md5(path.read_bytes()).hexdigest())
            self.assertEqual(entry["size"], path.stat().st_size)

    def test_refuses_non_ab_or_unknown_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, ota_type in (("EvolutionX-17.0-x.zip", "BLOCK"), ("other.zip", "AB")):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    ota_json.entry(self.package(directory, name, ota_type), "https://example.invalid/x")


if __name__ == "__main__":
    unittest.main()
