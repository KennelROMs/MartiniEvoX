#!/usr/bin/env python3
"""Configuration contracts, NOT Android build, boot, recovery, or OTA tests.

Uses stdlib unittest, git apply on disposable baseline fixtures (no git init),
and GNU Make on the actual relevant source sections and Android Make helpers.
Missing patches deliberately exercise the intact baseline for meaningful RED.
MARTINI_EROFS_PATCH_DIR may point at candidate patches before final export.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


CONTROL = Path(__file__).resolve().parents[1]
FIXTURE = CONTROL / "tests/fixtures/martini_erofs_config.before.json"
PATCH_DIR = Path(os.environ.get("MARTINI_EROFS_PATCH_DIR", CONTROL / "patches/martini-erofs"))
PATCHES = {"martini": "0001-device-enable-erofs.patch", "common": "0002-common-select-erofs.patch"}
BASES = {
    "martini": "3c226659a17d07f17a661e2571370af88cc16fb6",
    "common": "88ef16a01303b36544633ee55c2d9bf413d4bd3c",
}
BLOBS = {
    "martini": {
        "device.mk": "27c1097655bf00d70de74215e3ce408a57a23d09",
        "BoardConfig.mk": "0d0d21657b560b92c07b723141ec4673160d05d1",
        "lineage_martini.mk": "d36d76f63be5c8ac0113bb06b21f5b8f0bb8a28a",
    },
    "common": {
        "BoardConfigCommon.mk": "0822265e67bc516db23a54191f7eecae1f906600",
        "common.mk": "814b645a76ac711db1bbf0a704239a8b4cb50ea7",
        "init/Android.bp": "35919ffa2a518ea42753095e597f4d6e53ba58a6",
        "init/fstab.default": "0e873078a8b56542e41edfb2597db1795c888169",
    },
}
GET = "$(call soong_config_get,oneplus_sm8350,martini_erofs)"
ENABLE = "$(call soong_config_set_bool,oneplus_sm8350,martini_erofs,true)"
ENABLE_BLOCK = "# EROFS for martini's read-only system partitions.\n" + ENABLE + "\n\n"
FS_OVERRIDE = (
    "\nifeq (" + GET + ",true)\n"
    "BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := erofs\n"
    "BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := erofs\n"
    "BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := erofs\n"
    "endif\n"
)
RECOVERY_OVERRIDE = (
    "ifeq (" + GET + ",true)\n"
    "TARGET_RECOVERY_FSTAB := $(COMMON_PATH)/init/fstab.martini.erofs\n"
    "endif\n"
)
OTA_TYPE = "FILESYSTEM_TYPE_system=$(if $(filter true," + GET + "),erofs,ext4)"
SELECTOR = (
    '    src: select(soong_config_variable("oneplus_sm8350", "martini_erofs"), {\n'
    '        true: "fstab.martini.erofs",\n'
    '        default: "fstab.default",\n'
    '    }),'
)
SYSTEM_FS = ["BOARD_" + part + "IMAGE_FILE_SYSTEM_TYPE" for part in ("SYSTEM", "PRODUCT", "SYSTEM_EXT")]


def blob_id(source):
    raw = source.encode()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class TestMartiniErofsConfig(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text())
        temporary = tempfile.TemporaryDirectory(prefix="martini-erofs-contract-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        for repo, info in self.fixture["repositories"].items():
            for path, entry in info["files"].items():
                target = self.work / repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(entry["source"].encode())
            if (PATCH_DIR / PATCHES[repo]).is_file():
                self.git_apply(repo, "--check")
                self.git_apply(repo)

    def git_apply(self, repo, *options):
        result = subprocess.run(
            ["git", "apply", *options, str(PATCH_DIR / PATCHES[repo])],
            cwd=self.work / repo, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def before(self, repo, path):
        return self.fixture["repositories"][repo]["files"][path]["source"]

    def source(self, repo, path):
        target = self.work / repo / path
        self.assertTrue(target.is_file(), "Required martini EROFS source missing: " + path)
        return target.read_text()

    def test_fixture_provenance(self):
        for repo, expected in BASES.items():
            info = self.fixture["repositories"][repo]
            self.assertEqual(info["base_commit"], expected)
            self.assertEqual(set(info["files"]), set(BLOBS[repo]))
            for path, entry in info["files"].items():
                self.assertEqual(entry["blob"], BLOBS[repo][path])
                self.assertEqual(blob_id(entry["source"]), BLOBS[repo][path])
        helpers = self.fixture["soong_make_helpers"]
        self.assertEqual(helpers["base_commit"], "2fa923193db876e5be71f6094761600e7ade8b9f")
        self.assertEqual(helpers["blob"], "b355696f3a48741e9cf593d1e13a1406fadc1ce5")

    def test_only_martini_enables_typed_bool_before_common_inheritance(self):
        source = self.source("martini", "device.mk")
        self.assertEqual(source.count(ENABLE), 1, "martini must enable the single typed bool")
        inherit = "$(call inherit-product, device/oneplus/sm8350-common/common.mk)"
        self.assertLess(source.index(ENABLE), source.index(inherit))
        self.assertEqual(source.replace(ENABLE_BLOCK, ""), self.before("martini", "device.mk"))
        for repo in BASES:
            for path in (self.work / repo).rglob("*"):
                if path.is_file() and path != self.work / "martini/device.mk":
                    self.assertNotRegex(path.read_text(), r"soong_config_set[^\n]*martini_erofs")

    def evaluate_make(self, scenario):
        """A narrow harness: real product postinstall section before real Board section."""
        common = self.source("common", "common.mk").split("# A/B\n", 1)[1].split("# Audio\n", 1)[0]
        board = self.source("common", "BoardConfigCommon.mk").split("# Partitions\n", 1)[1].split("# RIL\n", 1)[0]
        (self.work / "postinstall.mk").write_text(common)
        values = SYSTEM_FS + [
            "TARGET_RECOVERY_FSTAB", "TARGET_USERIMAGES_USE_EXT4",
            "SOONG_CONFIG_oneplus_sm8350_martini_erofs",
            "SOONG_CONFIG_TYPE_oneplus_sm8350_martini_erofs",
            "AB_OTA_POSTINSTALL_CONFIG", "POSTINSTALL_BEFORE_BOARD",
            "BOARD_ONEPLUS_DYNAMIC_PARTITIONS_SIZE", "BOARD_SUPER_PARTITION_SIZE",
            "BOARD_ONEPLUS_DYNAMIC_PARTITIONS_PARTITION_LIST",
        ]
        text = self.fixture["soong_make_helpers"]["source"]
        # Only the common postinstall section is inherited; unrelated Android
        # dependencies are deliberately outside this configuration-only harness.
        text += (
            "\ninherit-product = $(if $(filter device/oneplus/sm8350-common/common.mk,$1),"
            "$(eval include postinstall.mk))\n"
        )
        if scenario == "martini":
            text += "include martini/device.mk\n"
        else:
            if scenario != "unset":
                text += "$(call soong_config_set_bool,oneplus_sm8350,martini_erofs," + scenario + ")\n"
            text += "include postinstall.mk\n"
        text += "POSTINSTALL_BEFORE_BOARD := $(AB_OTA_POSTINSTALL_CONFIG)\n"
        text += "COMMON_PATH := device/oneplus/sm8350-common\n" + board
        text += "\n" + "\n".join("$(info " + var + "=$(" + var + "))" for var in values)
        text += "\n.PHONY: all\nall:\n\t@:\n"
        makefile = self.work / "contract.mk"
        makefile.write_text(text)
        result = subprocess.run(
            ["make", "--no-print-directory", "-s", "-f", str(makefile)],
            cwd=self.work, capture_output=True, text=True,
            env={"PATH": os.environ["PATH"], "LC_ALL": "C"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        return dict(line.split("=", 1) for line in result.stdout.splitlines())

    def test_make_true_false_unset_and_real_martini_product_matrix(self):
        for scenario in ("true", "false", "unset", "martini"):
            with self.subTest(scenario=scenario):
                enabled = scenario in ("true", "martini")
                values = self.evaluate_make(scenario)
                for key in SYSTEM_FS:
                    self.assertEqual(values[key], "erofs" if enabled else "ext4")
                self.assertEqual(values["TARGET_RECOVERY_FSTAB"],
                                 "device/oneplus/sm8350-common/init/" +
                                 ("fstab.martini.erofs" if enabled else "fstab.default"))
                self.assertEqual(values["TARGET_USERIMAGES_USE_EXT4"], "true")
                self.assertEqual(values["SOONG_CONFIG_oneplus_sm8350_martini_erofs"], "true" if enabled else "")
                self.assertEqual(values["SOONG_CONFIG_TYPE_oneplus_sm8350_martini_erofs"], "" if scenario == "unset" else "bool")
                postinstall = values["AB_OTA_POSTINSTALL_CONFIG"].split()
                self.assertEqual(postinstall, values["POSTINSTALL_BEFORE_BOARD"].split())
                self.assertEqual(postinstall, [
                    "RUN_POSTINSTALL_system=true", "POSTINSTALL_PATH_system=system/bin/otapreopt_script",
                    "FILESYSTEM_TYPE_system=" + ("erofs" if enabled else "ext4"),
                    "POSTINSTALL_OPTIONAL_system=true", "RUN_POSTINSTALL_vendor=true",
                    "POSTINSTALL_PATH_vendor=bin/checkpoint_gc", "FILESYSTEM_TYPE_vendor=erofs",
                    "POSTINSTALL_OPTIONAL_vendor=true",
                ])
                self.assertEqual(values["BOARD_ONEPLUS_DYNAMIC_PARTITIONS_SIZE"], "5591007232")
                self.assertEqual(values["BOARD_SUPER_PARTITION_SIZE"], "11190403072")
                self.assertEqual(values["BOARD_ONEPLUS_DYNAMIC_PARTITIONS_PARTITION_LIST"],
                                 "odm product system system_ext vendor vendor_dlkm")

    def test_board_only_overrides_three_filesystems_and_recovery(self):
        source = self.source("common", "BoardConfigCommon.mk")
        self.assertEqual(source.count(FS_OVERRIDE), 1, "EROFS override must use the shared typed bool")
        self.assertEqual(source.count(RECOVERY_OVERRIDE), 1, "Recovery must use that same bool")
        self.assertEqual(source.replace(FS_OVERRIDE, "").replace(RECOVERY_OVERRIDE, ""),
                         self.before("common", "BoardConfigCommon.mk"))
        # Exact restoration guards capacities, partition lists, AVB, kernel,
        # SELinux, metadata EXT4 support, and all untouched Board defaults.
        for path in ("BoardConfig.mk", "lineage_martini.mk"):
            self.assertEqual(self.source("martini", path), self.before("martini", path))

    def test_ota_single_system_key_and_all_other_fields_and_packages_unchanged(self):
        source = self.source("common", "common.mk")
        self.assertEqual(source.count("FILESYSTEM_TYPE_system="), 1)
        self.assertIn(OTA_TYPE, source, "OTA must select from the product-stage bool, not Board FS variables")
        self.assertEqual(source.replace(OTA_TYPE, "FILESYSTEM_TYPE_system=ext4"), self.before("common", "common.mk"))
        self.assertIn("    fstab.default \\\n    fstab.default.vendor_ramdisk", source)

    def test_soong_boolean_selector_keeps_existing_module_and_output_names(self):
        source = self.source("common", "init/Android.bp")
        self.assertEqual(source.count(SELECTOR), 1, "fstab.default needs the bool select, with undefined/false default")
        self.assertEqual(source.replace(SELECTOR, '    src: "fstab.default",'), self.before("common", "init/Android.bp"))
        self.assertEqual(source.count('name: "fstab.default"'), 1)
        self.assertNotIn('name: "fstab.martini.erofs"', source)

    def test_shared_fstab_is_byte_identical_to_base(self):
        self.assertEqual(self.source("common", "init/fstab.default"), self.before("common", "init/fstab.default"))

    def test_martini_fstab_changes_exactly_three_rows_and_two_columns(self):
        base = self.before("common", "init/fstab.default")
        actual = self.source("common", "init/fstab.martini.erofs")
        expected = "".join(
            line.replace("ext4", "erofs", 1).replace("ro,barrier=1,discard", "ro", 1)
            if re.match(r"^(system|system_ext|product)\s", line) else line
            for line in base.splitlines(keepends=True)
        )
        self.assertEqual(actual, expected, "Preserve every other byte, including AVB keys, encryption, and comments")
        changed = []
        for old, new in zip(base.splitlines(), actual.splitlines()):
            if old != new:
                before, after = old.split(), new.split()
                self.assertEqual([i for i, pair in enumerate(zip(before, after)) if pair[0] != pair[1]], [2, 3])
                self.assertEqual(after[2:4], ["erofs", "ro"])
                changed.append(after[1])
        self.assertEqual(changed, ["/system", "/system_ext", "/product"])
        def mounts(text):
            return Counter(line.split()[1] for line in text.splitlines() if line.strip() and not line.startswith("#"))
        # The shared base already has two vold /storage/sdcard1 entries. Preserve
        # them; introduce no duplicates and keep each changed logical mount unique.
        self.assertEqual(mounts(actual), mounts(base))
        for mount in changed:
            self.assertEqual(mounts(actual)[mount], 1)

    def test_exact_five_file_patch_scope_and_reversibility(self):
        expected = {
            "martini": ["device.mk"],
            "common": ["BoardConfigCommon.mk", "common.mk", "init/Android.bp", "init/fstab.martini.erofs"],
        }
        for repo in BASES:
            with self.subTest(repo=repo):
                before = {path: entry["source"] for path, entry in self.fixture["repositories"][repo]["files"].items()}
                after = {str(path.relative_to(self.work / repo)): path.read_text()
                         for path in (self.work / repo).rglob("*") if path.is_file()}
                changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
                self.assertEqual(changed, expected[repo], "Only the five approved production files may change")
                self.assertEqual(sorted(line.split("\t")[2] for line in self.git_apply(repo, "--numstat").splitlines()), expected[repo])
                self.git_apply(repo, "--reverse", "--check")
                self.git_apply(repo, "--reverse")
                restored = {str(path.relative_to(self.work / repo)): path.read_text()
                            for path in (self.work / repo).rglob("*") if path.is_file()}
                self.assertEqual(restored, before)
        # No patch path can reach GApps selection, SettingsGoogle, signing files,
        # kernel sources, update_engine, or another device. The separate existing
        # SettingsGoogle test continues checking the official fixed blob.


if __name__ == "__main__":
    unittest.main(verbosity=2)
