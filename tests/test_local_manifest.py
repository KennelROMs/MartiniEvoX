#!/usr/bin/env python3
"""Contract tests for the martini local manifest.

Validates the dependency contract for adding OnePlus 9RT (martini, sm8350)
device support to Evolution-X before the XML is written (TDD RED phase).
Run from the control checkout: python3 -m unittest discover -s tests -v
"""

import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

CONTROL_DIR = os.environ.get(
    "MARTINI_EVOX_CONTROL_DIR", str(Path(__file__).resolve().parents[1])
)
MANIFEST_PATH = os.path.join(CONTROL_DIR, "manifests", "martini.xml")

# (remote-name, project-name, path, expected HEAD sha on lineage-24.0)
EXPECTED_PROJECTS = [
    (
        "martini-los",
        "android_device_oneplus_martini",
        "device/oneplus/martini",
        "3c226659a17d07f17a661e2571370af88cc16fb6",
    ),
    (
        "martini-los",
        "android_device_oneplus_sm8350-common",
        "device/oneplus/sm8350-common",
        "88ef16a01303b36544633ee55c2d9bf413d4bd3c",
    ),
    (
        "martini-los",
        "android_kernel_oneplus_sm8350",
        "kernel/oneplus/sm8350",
        "abd4ede9ec6463110b40360a4a772e1285e995dd",
    ),
    (
        "martini-los",
        "android_hardware_oplus",
        "hardware/oplus",
        "6e6f3dd8d41abbc99c30ce91e78d6cf5515607d0",
    ),
    (
        "martini-los",
        "android_hardware_pixelworks_interfaces",
        "hardware/pixelworks/interfaces",
        "462ccb7db689de0a92cafdde5efb3c81fa617448",
    ),
    (
        "martini-vendor",
        "proprietary_vendor_oneplus_martini",
        "vendor/oneplus/martini",
        "52ed9183111719515caa07a135dda7ce9e95de88",
    ),
    (
        "martini-vendor",
        "proprietary_vendor_oneplus_sm8350-common",
        "vendor/oneplus/sm8350-common",
        "445ead080f9ffb2be428405cea6e474e0fc3db05",
    ),
]

TRUSTED_FETCH_URLS = {
    "martini-los": "https://github.com/LineageOS/",
    "martini-vendor": "https://github.com/TheMuppets/",
}

# Canonical full clone URLs, written independently of EXPECTED_PROJECTS /
# TRUSTED_FETCH_URLS to catch org-duplication bugs (repo concatenates
# remote.fetch + project.name to build the clone URL, so project names must
# NOT carry the org prefix when the remote fetch URL already ends in the org).
# NOTE: the HEAD shas above are audit-time reference points on lineage-24.0,
# not pinned commitments — the XML pins the branch, not the commit.
CANONICAL_URLS = [
    ("device/oneplus/martini",
     "https://github.com/LineageOS/android_device_oneplus_martini"),
    ("device/oneplus/sm8350-common",
     "https://github.com/LineageOS/android_device_oneplus_sm8350-common"),
    ("kernel/oneplus/sm8350",
     "https://github.com/LineageOS/android_kernel_oneplus_sm8350"),
    ("hardware/oplus",
     "https://github.com/LineageOS/android_hardware_oplus"),
    ("hardware/pixelworks/interfaces",
     "https://github.com/LineageOS/android_hardware_pixelworks_interfaces"),
    ("vendor/oneplus/martini",
     "https://github.com/TheMuppets/proprietary_vendor_oneplus_martini"),
    ("vendor/oneplus/sm8350-common",
     "https://github.com/TheMuppets/proprietary_vendor_oneplus_sm8350-common"),
]

# Paths that already exist in the Evolution-X manifest snapshot and must NOT
# be re-added (guarded against regression / duplication).
ALREADY_TRACKED_PATHS = {
    "hardware/qcom-caf/common",
    "hardware/qcom-caf/sm8350/audio",
    "hardware/qcom-caf/sm8350/display",
    "vendor/extras",
}


def load_manifest_root():
    if not os.path.isfile(MANIFEST_PATH):
        raise FileNotFoundError(
            "target manifest not found: %s (write it after watching this "
            "test fail first)" % MANIFEST_PATH
        )
    return ET.parse(MANIFEST_PATH).getroot()


class TestMartiniLocalManifest(unittest.TestCase):
    def test_manifest_file_exists(self):
        self.assertTrue(
            os.path.isfile(MANIFEST_PATH),
            "manifests/martini.xml must exist at %s" % MANIFEST_PATH,
        )

    def test_manifest_is_valid_xml_with_manifest_root(self):
        root = load_manifest_root()
        self.assertEqual(root.tag, "manifest")

    def test_seven_projects_with_exact_unique_paths_and_revisions(self):
        root = load_manifest_root()
        projects = root.findall("project")
        self.assertEqual(
            len(projects),
            7,
            "expected exactly 7 <project> entries, got %d" % len(projects),
        )
        seen_paths = []
        for remote, name, path, _ in EXPECTED_PROJECTS:
            matches = [p for p in projects if p.get("path") == path]
            self.assertEqual(
                len(matches),
                1,
                "path %s must appear exactly once (got %d)"
                % (path, len(matches)),
            )
            proj = matches[0]
            seen_paths.append(path)
            self.assertEqual(
                proj.get("name"),
                name,
                "project at %s must have name %s" % (path, name),
            )
            self.assertEqual(
                proj.get("remote"),
                remote,
                "project %s must use remote %s" % (name, remote),
            )
            self.assertEqual(
                proj.get("revision"),
                "lineage-24.0",
                "project %s must pin revision lineage-24.0" % name,
            )
        # uniqueness across all entries, not just expected ones
        all_paths = [p.get("path") for p in projects]
        self.assertEqual(len(all_paths), len(set(all_paths)),
                         "paths must be unique")
        self.assertEqual(
            sorted(all_paths),
            sorted(seen_paths),
            "manifest paths must match the 7 expected paths exactly",
        )

    def test_remotes_defined_with_trusted_fetch_urls(self):
        root = load_manifest_root()
        remotes = root.findall("remote")
        by_name = {r.get("name"): r for r in remotes}
        for name, fetch in TRUSTED_FETCH_URLS.items():
            self.assertIn(
                name, by_name, "remote %s must be defined" % name
            )
            self.assertEqual(
                by_name[name].get("fetch"),
                fetch,
                "remote %s must fetch from trusted URL %s" % (name, fetch),
            )
        # no extra remotes beyond the two custom ones
        self.assertEqual(
            set(by_name), set(TRUSTED_FETCH_URLS),
            "only the two custom remotes should be defined, got %s"
            % sorted(by_name),
        )

    def test_repo_url_concatenation_yields_canonical_urls(self):
        """Simulate repo's clone-URL construction: fetch.rstrip('/') + '/' + name.

        Independent literals in CANONICAL_URLS guard against org duplication
        (e.g. https://github.com/LineageOS/LineageOS/android_device_...).
        """
        root = load_manifest_root()
        remotes = {r.get("name"): r.get("fetch") for r in root.findall("remote")}
        by_path = {p.get("path"): p for p in root.findall("project")}
        for path, canonical in CANONICAL_URLS:
            self.assertIn(path, by_path,
                          "path %s missing from manifest" % path)
            proj = by_path[path]
            fetch = remotes[proj.get("remote")]
            computed = fetch.rstrip("/") + "/" + proj.get("name")
            self.assertEqual(
                computed, canonical,
                "repo would clone %s from %s (expected %s). "
                "Project names must not repeat the org already in the "
                "remote fetch URL." % (path, computed, canonical),
            )

    def test_no_remove_project_entries(self):
        root = load_manifest_root()
        removes = root.findall("remove-project")
        self.assertEqual(
            len(removes),
            0,
            "local manifest must not contain remove-project entries",
        )

    def test_no_already_tracked_paths_reintroduced(self):
        root = load_manifest_root()
        paths = {p.get("path") for p in root.findall("project")}
        overlap = paths & ALREADY_TRACKED_PATHS
        self.assertEqual(
            overlap,
            set(),
            "paths already tracked upstream must not be re-added: %s"
            % sorted(overlap),
        )

    def test_no_copy_elements_or_extra_elements(self):
        root = load_manifest_root()
        allowed = {"remote", "project"}
        for child in root:
            self.assertIn(
                child.tag,
                allowed,
                "unexpected element <%s> in local manifest" % child.tag,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
