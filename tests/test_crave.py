# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
"""crave.sh publishes only a ROM/KSU pair from one CONTROL commit, with a matching Updater entry."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


CONTROL = Path(__file__).resolve().parents[1]
ZIP = "EvolutionX-17.0-20261008-martini-12.2-Unofficial.zip"


class CraveUploadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", self.tmp])
        self.head = subprocess.run(["git", "-C", CONTROL, "rev-parse", "HEAD"], check=True,
                                   capture_output=True, text=True).stdout.strip()
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for tool in ("rsync", "ssh"):
            fake = bin_dir / tool
            fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{self.tmp}/{tool}.args"\n')
            fake.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", SF_USER="maint",
                        SF_PROJECT="kennelroms", MARTINI_CONTROL=str(self.tmp / "control"))
        subprocess.run(["git", "clone", "--quiet", CONTROL, self.tmp / "control"], check=True)

    def run_dir(self, name, kernel, commit):
        directory = self.tmp / "source/artifacts" / name
        directory.mkdir(parents=True)
        (directory / "result.json").write_text(json.dumps(
            {"status": "BUILT_AND_ARCHIVED_UNVALIDATED", "kernel": kernel, "control_commit": commit}))
        return directory

    def upload(self, rom, ksu):
        with zipfile.ZipFile(rom / ZIP, "w") as archive:
            archive.writestr("META-INF/com/android/metadata", "ota-type=AB\npost-timestamp=1791500000\n")
        (ksu / ZIP.replace(".zip", "-ksu-boot.img")).write_bytes(b"boot")
        return subprocess.run(["bash", CONTROL / "tools/crave.sh", "upload", rom, ksu],
                              cwd=self.tmp / "source", env=self.env, capture_output=True, text=True)

    def test_uploads_pair_and_writes_entry(self):
        rom = self.run_dir("run-rom", "normal", self.head)
        ksu = self.run_dir("run-ksu", "ksu", self.head)
        result = self.upload(rom, ksu)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = (self.tmp / "rsync.args").read_text().splitlines()
        self.assertEqual(args[-3:], [str(rom / ZIP), str(ksu / ZIP.replace(".zip", "-ksu-boot.img")),
                                     "maint@frs.sourceforge.net:/home/frs/project/kennelroms/martini/"])
        entry = json.loads((rom / "martini.json").read_text())["response"][0]
        self.assertEqual(entry["download"],
                         f"https://sourceforge.net/projects/kennelroms/files/martini/{ZIP}/download")
        self.assertEqual(entry["timestamp"], 1791500000)

    def test_refuses_runs_from_different_commits(self):
        rom = self.run_dir("run-rom", "normal", self.head)
        ksu = self.run_dir("run-ksu", "ksu", "0" * 40)
        result = self.upload(rom, ksu)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not pair", result.stderr)
        self.assertFalse((self.tmp / "rsync.args").exists())


if __name__ == "__main__":
    unittest.main()
