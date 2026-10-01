#!/usr/bin/env python3
"""Actual Make recipe contracts, not Android build or OTA runtime tests."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


CONTROL = Path(__file__).resolve().parents[1]
FIXTURE = CONTROL / 'tests/fixtures/target_files_retention.before.json'
PATCH = CONTROL / 'patches/vendor_lineage_target_files/0001-optional-target-files-retention.patch'
CLEANUP = '\t$(hide) rm -rf $(call intermediates-dir-for,PACKAGING,target_files)\n'
GUARDED = 'ifneq ($(EVO_KEEP_TARGET_FILES),true)\n' + CLEANUP + 'endif\n'


class TestTargetFilesRetention(unittest.TestCase):
    def setUp(self):
        fixture = json.loads(FIXTURE.read_text())
        self.assertEqual(fixture['base_commit'], 'ab335e0ba751d5bde019f48e1935922f7afd62e4')
        raw = fixture['source'].encode()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        self.assertEqual(blob, '939f7edeb1dc8234cca4f9412903ddd743f40f45')
        self.assertEqual(fixture['blob'], blob)

        temporary = tempfile.TemporaryDirectory(prefix='target-files-contract-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        repo = self.root / 'vendor/lineage'
        recipe = repo / 'build/tasks/evolution.mk'
        recipe.parent.mkdir(parents=True)
        recipe.write_bytes(raw)
        if PATCH.is_file():
            for flags in (['--check'], []):
                result = subprocess.run(
                    ['git', 'apply', *flags, str(PATCH)], cwd=repo,
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(recipe.read_text(), fixture['source'].replace(CLEANUP, GUARDED))

        # Only non-archive presentation/JSON helpers are inert in this isolated
        # fixture. mv, sha256sum, sed, and conditional directory cleanup are real.
        for relative in ('build/tools/createjson.py', 'build/tasks/ascii_output.sh'):
            helper = repo / relative
            helper.parent.mkdir(parents=True, exist_ok=True)
            helper.write_text('#!/bin/sh\nexit 0\n')
            helper.chmod(0o755)

        self.out = self.root / 'out/target/product/martini'
        self.intermediates = self.out / 'obj/PACKAGING/target_files_intermediates'
        self.meta = self.intermediates / 'lineage_martini-target_files/META'
        self.meta.mkdir(parents=True)
        self.metadata = {
            'misc_info.txt': b'system_fs_type=erofs\n',
            'postinstall_config.txt': b'FILESYSTEM_TYPE_system=erofs\n',
            'dynamic_partitions_info.txt': b'super_partition_size=11190403072\n',
        }
        for name, data in self.metadata.items():
            (self.meta / name).write_bytes(data)
        self.package = b'Isolated fixture OTA bytes; not a flashable archive.\n'
        self.input_package = self.out / 'lineage_martini-ota.zip'
        self.input_package.write_bytes(self.package)
        (self.root / 'harness.mk').write_text(
            'PRODUCT_OUT := out/target/product/martini\n'
            'LINEAGE_VERSION := EvolutionX-contract\n'
            'INTERNAL_OTA_PACKAGE_TARGET := $(PRODUCT_OUT)/lineage_martini-ota.zip\n'
            'TARGET_DEVICE := martini\n'
            'TARGET_BUILD_VARIANT := userdebug\n'
            'WITH_GMS := true\n'
            'DEFAULT_GOAL := fixture-default\n'
            'hide := @\n'
            'intermediates-dir-for = $(PRODUCT_OUT)/obj/PACKAGING/target_files_intermediates\n'
            'include vendor/lineage/build/tasks/evolution.mk\n'
            '.PHONY: fixture-default\n'
            'fixture-default:\n\t@:\n'
        )

    def run_recipe(self, keep=None):
        environment = os.environ.copy()
        for key in ('EVO_KEEP_TARGET_FILES', 'MAKEFLAGS', 'MFLAGS', 'MAKEOVERRIDES'):
            environment.pop(key, None)
        sha256sum = shutil.which('sha256sum')
        self.assertIsNotNone(sha256sum)
        command = ['make', '--no-print-directory', '-s', '-f', 'harness.mk',
                   'SHA256=' + sha256sum, 'evolution']
        if keep is not None:
            command.append('EVO_KEEP_TARGET_FILES=' + keep)
        result = subprocess.run(command, cwd=self.root, env=environment,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        final = self.out / 'EvolutionX-contract.zip'
        self.assertEqual(final.read_bytes(), self.package)
        self.assertFalse(self.input_package.exists())
        expected = hashlib.sha256(self.package).hexdigest() + '  EvolutionX-contract.zip\n'
        self.assertEqual((self.out / 'EvolutionX-contract.zip.sha256sum').read_text(), expected)

    def test_unset_preserves_original_cleanup(self):
        self.run_recipe()
        self.assertFalse(self.intermediates.exists())

    def test_false_preserves_original_cleanup(self):
        self.run_recipe('false')
        self.assertFalse(self.intermediates.exists())

    def test_true_preserves_original_target_files_metadata(self):
        self.run_recipe('true')
        self.assertTrue(self.meta.is_dir(), 'Explicit keep=true must retain original target-files')
        for name, data in self.metadata.items():
            self.assertEqual((self.meta / name).read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
