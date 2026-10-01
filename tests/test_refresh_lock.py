# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for pinning a merged manifest; no Repo or network."""

import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


CONTROL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("refresh_lock", CONTROL / "tools/refresh_lock.py")
refresh_lock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh_lock)

MERGED = """<manifest>
  <remote name="aosp" fetch="https://android.googlesource.com" revision="refs/tags/android-17.0.0_r1"/>
  <remote name="evo" fetch="https://github.com/Evolution-X" revision="refs/heads/cnb"/>
  <remote name="github" fetch=".."/>
  <remote name="private" fetch="ssh://git@github.com"/>
  <default remote="github" revision="refs/heads/lineage-24.0"/>
  <project name="platform/art" path="art" remote="aosp"/>
  <project name="bionic" remote="evo"/>
  <project name="LineageOS/android_vendor_apn" path="vendor/apn"/>
  <project name="prebuilt" remote="evo" clone-depth="1" revision="0123456789012345678901234567890123456789"/>
</manifest>"""


class RefreshLockTests(unittest.TestCase):
    def test_pin_resolves_every_project_and_keeps_locks_syncable(self):
        asked = []

        def resolve(url, expr):
            asked.append((url, expr))
            return expr if refresh_lock.SHA.match(expr) else str(len(asked)) * 40

        root = refresh_lock.pin(ET.fromstring(MERGED), resolve)
        remotes = {r.get("name"): r.get("fetch") for r in root.findall("remote")}
        self.assertEqual(remotes["github"], "https://github.com")
        self.assertNotIn("private", remotes)
        self.assertIn(("https://github.com/LineageOS/android_vendor_apn", "refs/heads/lineage-24.0"), asked)
        self.assertIn(("https://android.googlesource.com/platform/art", "refs/tags/android-17.0.0_r1"), asked)
        projects = {p.get("path", p.get("name")): p for p in root.findall("project")}
        for project in projects.values():
            self.assertRegex(project.get("revision"), r"^[0-9a-f]{40}$|^\d{40}$")
        self.assertEqual(projects["bionic"].get("upstream"), "refs/heads/cnb")
        self.assertEqual(projects["bionic"].get("clone-depth"), "1")
        self.assertIsNone(projects["vendor/apn"].get("clone-depth"))
        # An already pinned SHA is kept and gets no branch attributes.
        self.assertEqual(projects["prebuilt"].get("revision"), "0123456789012345678901234567890123456789")
        self.assertIsNone(projects["prebuilt"].get("upstream"))

    def test_ls_remote_prefers_peeled_tag_and_refuses_unknown_refs(self):
        output = ("a" * 40 + "\trefs/heads/cnb\n" + "b" * 40 + "\trefs/tags/v1\n"
                  + "c" * 40 + "\trefs/tags/v1^{}\n")
        self.assertEqual(refresh_lock.parse_ls_remote(output, "cnb"), "a" * 40)
        self.assertEqual(refresh_lock.parse_ls_remote(output, "refs/tags/v1"), "c" * 40)
        with self.assertRaises(refresh_lock.RefreshError):
            refresh_lock.parse_ls_remote(output, "lineage-24.0")


if __name__ == "__main__":
    unittest.main()
