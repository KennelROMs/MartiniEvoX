#!/usr/bin/env python3
"""Contract for the floating martini local manifest used by refresh_lock.py."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

MANIFEST = Path(__file__).resolve().parents[1] / "manifests" / "martini.xml"

# path -> (canonical clone URL, floating branch)
EXPECTED = {
    "device/oneplus/martini": ("https://github.com/LineageOS/android_device_oneplus_martini", "lineage-24.0"),
    "device/oneplus/sm8350-common": ("https://github.com/LineageOS/android_device_oneplus_sm8350-common", "lineage-24.0"),
    "kernel/oneplus/sm8350": ("https://github.com/LineageOS/android_kernel_oneplus_sm8350", "lineage-24.0"),
    "kernel/oneplus/sm8350-ksu": ("https://github.com/LineageOS/android_kernel_oneplus_sm8350", "lineage-24.0"),
    "hardware/oplus": ("https://github.com/PixelOS-AOSP/android_hardware_oplus", "seventeen"),
    "hardware/pixelworks/interfaces": ("https://github.com/LineageOS/android_hardware_pixelworks_interfaces", "lineage-24.0"),
    "vendor/oneplus/martini": ("https://github.com/TheMuppets/proprietary_vendor_oneplus_martini", "lineage-24.0"),
    "vendor/oneplus/sm8350-common": ("https://github.com/TheMuppets/proprietary_vendor_oneplus_sm8350-common", "lineage-24.0"),
    "vendor/oplus/camera": ("https://gitlab.com/NoPrincessHere/proprietary_vendor_oplus_camera", "seventeen"),
    "vendor/oneplus/dolby": ("https://gitlab.com/NoPrincessHere/proprietary_vendor_oneplus_dolby", "seventeen"),
    "packages/apps/DolbyAtmos": ("https://github.com/PixelOS-AOSP/android_packages_apps_DolbyAtmos", "seventeen"),
    "external/KernelSU-Next": ("https://github.com/KernelSU-Next/KernelSU-Next", "legacy"),
}


class TestMartiniLocalManifest(unittest.TestCase):
    def test_projects_resolve_to_expected_repositories_and_branches(self):
        root = ET.parse(MANIFEST).getroot()
        self.assertEqual({child.tag for child in root}, {"remote", "project"})
        remotes = {r.get("name"): r.get("fetch") for r in root.findall("remote")}
        projects = root.findall("project")
        paths = [p.get("path") for p in projects]
        self.assertEqual(len(paths), len(set(paths)))
        actual = {p.get("path"): (remotes[p.get("remote")].rstrip("/") + "/" + p.get("name"),
                                  p.get("revision")) for p in projects}
        self.assertEqual(actual, EXPECTED)
        # Kbuild unshallows a shallow KernelSU-Next checkout over the network.
        self.assertTrue(all(p.get("clone-depth") is None for p in projects))


if __name__ == "__main__":
    unittest.main()
