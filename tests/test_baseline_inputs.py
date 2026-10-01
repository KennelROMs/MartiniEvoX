#!/usr/bin/env python3
"""Offline contracts for the locked baseline, patch series and build profile.

Golden identities come from the historical candidate and offline source review.
Excluded evidence, SettingsGoogle source/patch/fixture and Android workspaces are
not test inputs. These tests do not import bundles, invoke Git or run a build.
"""

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "baselines/20260930-a8114027.json"
MANIFEST = "manifests/locked/martini-20260930.xml"
# Active inputs derived from the historical candidate lock above.
ACTIVE_BASELINE = "baselines/20261001-pixel.json"
ACTIVE_MANIFEST = "manifests/locked/martini-20261001-pixel.xml"
KSU_KERNEL = "kernel/oneplus/sm8350-ksu"
KSU_SOURCE = "external/KernelSU-Next"
KSU_REVISION = "cd739c78802333455391df973db17d9f28328b83"
SERIES = "patches/series.json"
SOURCE = "sources/settings-google.json"
SETTINGS_PATCH_BYTES = 1357
HISTORICAL_SETTINGS_PATCH = "patches/vendor_google_apps_SettingsGoogle/0001-fix-screen-collector.patch"
ORIGINAL_MANIFEST_SHA = "e8135adbccc1b4dea97ec2b7b2cf8e063ef99b3d0254b1faa3f10bf5c13c40e7"
PORTABLE_MANIFEST_SHA = "cd2e2bc80dd622307279e70d41d3f44496936bf7e660a23a9879aabddf3aac85"
FINGERPRINTS = {
    "original_tree": "0be27ed82eb138376a18c47ef60daa3d56623b1a7ad56fc9a41557b166704ae0",
    "portable_tree": "6bf1c7f04b71a3cef1422453a8c1383f65dbb5ad4350e3784dd8883afa2176c2",
    "ordered_project_subtrees": "5de31751995d8dcdc7fc6cb2d1e718e1faa40035caf89e8d716ca199db92284e",
    "sorted_path_name_revision_set": "9707df61ec5c142995172bcf121039dfdfba12a4b90d7c003a3dbddcbeea092c",
    "ordered_copy_link_records": "0f1afa9afd8e116d14a2f4aa827d224b67697d51c4fd348b1fed625133c14fe6",
}
HEADS = {
    "device/oneplus/martini": "3c226659a17d07f17a661e2571370af88cc16fb6",
    "device/oneplus/sm8350-common": "88ef16a01303b36544633ee55c2d9bf413d4bd3c",
    "vendor/google/apps/SettingsGoogle": "86a6033a534f7e8039e3af6b7e53c9e244621512",
    "system/update_engine": "5b9591570c6603d73ab86f8526f4280ccfea1849",
    "vendor/lineage": "ab335e0ba751d5bde019f48e1935922f7afd62e4",
    "kernel/oneplus/sm8350": "abd4ede9ec6463110b40360a4a772e1285e995dd",
}
PATCHES = [
    ("martini-device-erofs", "device/oneplus/martini", "patches/martini-erofs/0001-device-enable-erofs.patch",
     "15a5155d7897c646e3855adff149e03a19ff0a8d10870b66d15d685adbb6c7c3"),
    ("martini-common-erofs", "device/oneplus/sm8350-common", "patches/martini-erofs/0002-common-select-erofs.patch",
     "1313947fc3451a5fc63267e36704958fa6c2faa358dd7ecfff60dfa7094f06b2"),
    ("settings-google-collector", "vendor/google/apps/SettingsGoogle", None,
     "039b2f1591745b6168eef871cef9aebd135b0a48981979e4ece0206cdf109359"),
    ("update-engine-signature", "system/update_engine", "patches/update_engine-payload-verification/0001-restore-payload-signature-verification.patch",
     "52810228ca9a2750d5c14ad792f9f5b83623dac64867f622bd492ffbb28129f0"),
    ("update-engine-backuptool", "system/update_engine", "patches/update_engine-erofs-backuptool/0002-guard-erofs-backuptool.patch",
     "794477b1f3b0b2a788d50002c442ff8727ac4a45f1735e6c1e6dcba6809f8419"),
    ("vendor-lineage-retention", "vendor/lineage", "patches/vendor_lineage_target_files/0001-optional-target-files-retention.patch",
     "06bdcdef5cc681f3bb9e5bb08fd3815420355bb9f58e42847dff4417863da5fd"),
]
PATCHED_SOURCE_HASHES = {
    "device/oneplus/martini/device.mk": "ba190b2b1689fb0c34bd1a5beb935c6a07392a748bd7b176de2d9a23b9cda19c",
    "device/oneplus/sm8350-common/BoardConfigCommon.mk": "9ca442c4d175156f98fc9bae6e5450a9551d17f53ca8cfc1bf871eb0bf2d56e8",
    "device/oneplus/sm8350-common/common.mk": "8d2affbeef3fe2bbc313d039a2f3f3feb715f43111f67c20957cc4d9f117f38b",
    "device/oneplus/sm8350-common/init/Android.bp": "495eb9327aa79b6a30f9db9b53314123a37a542dabbaf01f3d3a71690ed1d982",
    "device/oneplus/sm8350-common/init/fstab.martini.erofs": "7ee7e077f189b90d4dc7240b3b781c63006c726182295c5958e91227a069a7d6",
    "vendor/google/apps/SettingsGoogle/src/com/google/android/settings/SettingsGoogleScreenCollector.java": "912e8d441193655aa21e9986d251140983a5f338e7b4798df884d9592156225a",
}
BUNDLE_SHA = "57eafcf7b3a9b4823bf2b0404ab2673b9c9438e1d0bebb8f51531c36e8c67179"
BUNDLE_BYTES = 1648368
CORRECTED = "f38977d0fcfd117e76d5f18e4bbd453884122a4e"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def element_record(element):
    """Ignore XML formatting, preserve all attributes and child order."""
    return [element.tag, dict(element.attrib), [element_record(c) for c in element]]


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


class TestBaselineInputs(unittest.TestCase):
    def relative_path(self, value):
        self.assertIsInstance(value, str)
        path = PurePosixPath(value)
        self.assertTrue(value and not path.is_absolute(), value)
        self.assertNotIn("..", path.parts, value)
        self.assertNotIn("\\", value)
        return ROOT / value

    def required_file(self, relative):
        path = self.relative_path(relative)
        self.assertTrue(path.is_file(), "Missing required control input: " + relative)
        return path

    def load_json(self, relative):
        value = json.loads(self.required_file(relative).read_text())
        self.assertEqual(value["schema_version"], 1)
        return value

    def test_locked_manifest_byte_identity_and_provenance(self):
        raw = self.required_file(MANIFEST).read_bytes()
        self.assertEqual(len(raw), 308227)
        self.assertEqual(sha256(raw), PORTABLE_MANIFEST_SHA)
        manifest = self.load_json(BASELINE)["manifest"]
        self.assertEqual(manifest["original"], {
            "record": "docs/status/evidence/2026-09-30-candidate/manifest.lock.xml",
            "bytes": 308267, "sha256": ORIGINAL_MANIFEST_SHA,
        })
        self.assertEqual(manifest["portable"], {
            "path": MANIFEST, "bytes": len(raw), "sha256": PORTABLE_MANIFEST_SHA,
        })
        self.assertEqual(manifest["semantic_fingerprints"], FINGERPRINTS)

    def test_only_allowed_remote_normalization(self):
        root = ET.fromstring(self.required_file(MANIFEST).read_bytes())
        self.assertEqual(fingerprint(element_record(root)), FINGERPRINTS["portable_tree"])
        remotes = root.findall("remote")
        self.assertEqual(len(remotes), 10)
        self.assertNotIn("private", {e.get("name") for e in remotes})
        github = next(e for e in remotes if e.get("name") == "github")
        self.assertEqual(github.attrib, {
            "name": "github", "fetch": "https://github.com", "review": "review.lineageos.org",
        })
        self.assertTrue(all(e.get("fetch", "").startswith("https://") for e in remotes))
        self.assertFalse(any(e.get("remote") == "private" for e in root.iter()))
        # Reverse only the two approved operations, then compare the entire tree.
        original = copy.deepcopy(root)
        next(e for e in original.findall("remote") if e.get("name") == "github").set("fetch", "..")
        original.insert(len(remotes), ET.Element("remote", {"name": "private", "fetch": "ssh://git@github.com"}))
        self.assertEqual(fingerprint(element_record(original)), FINGERPRINTS["original_tree"])
        self.assertEqual(self.load_json(BASELINE)["manifest"]["allowed_normalizations"], [
            {"operation": "set_remote_fetch", "name": "github", "from": "..", "to": "https://github.com"},
            {"operation": "remove_unused_remote", "attributes": {"name": "private", "fetch": "ssh://git@github.com"}},
        ])

    def test_all_project_and_copy_link_records_preserved(self):
        root = ET.fromstring(self.required_file(MANIFEST).read_bytes())
        projects = root.findall("project")
        self.assertEqual(len(projects), 1262)
        self.assertEqual(self.load_json(BASELINE)["manifest"]["project_count"], 1262)
        paths = [p.get("path", p.get("name")) for p in projects]
        self.assertEqual(len(paths), len(set(paths)))
        for project, path in zip(projects, paths):
            self.relative_path(path)
            self.assertRegex(project.get("revision", ""), r"^[0-9a-f]{40}$")
            self.assertTrue(project.get("name"))
        self.assertEqual(fingerprint([element_record(p) for p in projects]), FINGERPRINTS["ordered_project_subtrees"])
        triples = sorted([[p.get("path", p.get("name")), p.get("name"), p.get("revision")] for p in projects])
        self.assertEqual(fingerprint(triples), FINGERPRINTS["sorted_path_name_revision_set"])
        children = [[p.get("path", p.get("name")), element_record(c)] for p in projects for c in p]
        self.assertEqual(sum(c[1][0] == "copyfile" for c in children), 1)
        self.assertEqual(sum(c[1][0] == "linkfile" for c in children), 25)
        self.assertEqual(fingerprint(children), FINGERPRINTS["ordered_copy_link_records"])

    def test_patch_bytes_order_and_base_heads_match_candidate(self):
        baseline = self.load_json(BASELINE)
        series = self.load_json(SERIES)
        self.assertEqual(baseline["repo_heads"], HEADS)
        self.assertEqual(series["baseline"], ACTIVE_BASELINE)
        active = self.load_json(ACTIVE_BASELINE)["repo_heads"]
        projects = ET.fromstring(self.required_file(ACTIVE_MANIFEST).read_bytes()).findall("project")
        revisions = {p.get("path", p.get("name")): p.get("revision") for p in projects}
        for repo, revision in HEADS.items():
            self.assertEqual(revisions[repo], revision)
            self.assertEqual(active[repo], revision)
        for entry in series["patches"]:
            self.assertEqual(entry["base_revision"], active[entry["repo"]])
            self.assertEqual(entry["base_revision"], revisions[entry["repo"]])
        expected = []
        for name, repo, patch, digest in PATCHES:
            entry = {"id": name, "repo": repo, "base_revision": HEADS[repo], "sha256": digest}
            if patch is None:
                entry.update(external_input="settings_google_patch", bytes=SETTINGS_PATCH_BYTES)
            else:
                entry["patch"] = patch
            expected.append(entry)
        # The candidate's patch set stays first and unchanged; later work only appends.
        self.assertEqual(series["patches"][:len(expected)], expected)
        source = self.load_json(SOURCE)
        for entry in series["patches"]:
            self.relative_path(entry["repo"])
            if "patch" in entry:
                self.assertEqual(sha256(self.required_file(entry["patch"]).read_bytes()), entry["sha256"])
            else:
                external = source["external_inputs"][entry["external_input"]]
                self.assertEqual(external["type"], "git-diff")
                self.assertEqual(external["sha256"], entry["sha256"])
                self.assertEqual(external["bytes"], entry["bytes"])
                self.assertIs(external["included"], False)
                self.assertEqual(source["status"], "BLOCKED")

    def test_diffs_use_git_apply_without_reexport_or_commits(self):
        series = self.load_json(SERIES)
        self.assertEqual(series["apply"], "git apply")
        self.assertEqual(series["check"], "git apply --check")
        self.assertEqual(series["order"], "patches-array-order")
        self.assertIs(series["require_clean_worktree_before_series"], True)
        self.assertEqual(series["on_mismatch"], "stop-and-inspect")
        self.assertEqual(series["already_applied"], "stop-and-inspect")
        self.assertNotIn("git am", json.dumps(series))
        kernel = {}
        for entry in series["patches"]:
            if entry["repo"].startswith("kernel/"):
                kernel.setdefault(entry["repo"], []).append(entry["patch"])
        # KSU changes only exist in their own checkout; both kernels share the same other patches.
        ksu_only = [p for p in kernel[KSU_KERNEL] if p.startswith("patches/ksu/")]
        self.assertEqual([p for p in kernel[KSU_KERNEL] if p not in ksu_only], kernel["kernel/oneplus/sm8350"])
        self.assertEqual(set(kernel), {"kernel/oneplus/sm8350", KSU_KERNEL})
        self.assertTrue(ksu_only)

    def test_candidate_identity_and_historical_trust_scope(self):
        baseline = self.load_json(BASELINE)
        self.assertEqual(baseline["id"], "martini-20260930-a8114027")
        self.assertEqual(baseline["candidate_rom"], {
            "filename": "EvolutionX-17.0-20260930-martini-12.2-Unofficial.zip",
            "bytes": 3648582850,
            "sha256": "a8114027f2a22ff1f16ef042a3fd4562487f03599844d9525d95e3668bfce9a8",
            "role": "historical-identity-not-a-prebuild-input",
        })
        self.assertEqual(baseline["patched_source_sha256"], PATCHED_SOURCE_HASHES)
        self.assertEqual(baseline["signing"]["recorded_candidate_checks"], {
            "payload_signature_positive_exit": 0,
            "payload_signature_wrong_key_exit": 1,
            "whole_file_signature_exit": 0,
        })
        self.assertEqual(baseline["signing"]["configuration"], "inherited-no-key-changes")
        self.assertIs(baseline["signing"]["private_keys_included"], False)
        self.assertIs(baseline["signing"]["public_release_trust_claimed"], False)
        self.assertEqual(baseline["avb"]["top_flags"], 3)
        self.assertEqual(baseline["avb"]["key_scope"], "inherited-public-AOSP-test-key")
        self.assertEqual(baseline["avb"]["recorded_expected_key_slots_chain_exit"], 0)
        self.assertIs(baseline["avb"]["enforced_device_verified_boot_claimed"], False)
        self.assertEqual(baseline["kernel"], {
            "profile": "normal", "repo": "kernel/oneplus/sm8350",
            "base_revision": HEADS["kernel/oneplus/sm8350"], "ksu_enabled": False,
            "historical_output_hashes_required": False,
        })
        self.assertTrue(all(not p.startswith("out/") for p in baseline["patched_source_sha256"]))
        for value in baseline["evidence_records"].values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")
        self.assertEqual(baseline["evidence_records"]["docs/status/evidence/2026-09-30-candidate/metadata.json"],
                         "f670e348a7a34489b98ad25d96483ee6f94ce1e0f03e955d26a558f96f50a74f")
        self.assertEqual(baseline["evidence_records"]["docs/status/evidence/2026-09-30-candidate/build-archive-summary.json"],
                         "3c9d63496efffe377f7598b5d3fba58a27aeba5b1320e47464db140264a663a3")

    def test_profile_uses_locked_inputs_and_normal_build_rules(self):
        profile = self.load_json("profiles/martini.json")
        self.assertEqual(profile["device"], "martini")
        for key, path in {"baseline": ACTIVE_BASELINE, "manifest": ACTIVE_MANIFEST,
                          "patch_series": SERIES}.items():
            self.assertEqual(profile[key], path)
            self.required_file(path)
        self.assertEqual(profile["source_restores"], [SOURCE])
        self.required_file(SOURCE)
        self.assertEqual(profile["lunch"], "lineage_martini-cp2a-userdebug")
        self.assertEqual(profile["target"], "evolution")
        self.assertEqual(profile["environment"], {"EVO_KEEP_TARGET_FILES": "true"})
        self.assertEqual(profile["kernel_variants"], {"normal": {}, "ksu": {"MARTINI_KSU": "true"}})
        self.assertEqual(profile["erofs_partitions"], ["odm", "product", "system", "system_ext", "vendor", "vendor_dlkm"])
        self.assertEqual(profile["prebuild"], {
            "required_inputs": ["locked-manifest", "base-revisions", "patch-sha256", "source-restores"],
            "requires_existing_out": False, "requires_historical_artifacts": False,
        })
        self.assertEqual(profile["independent_rebuild"], {
            "status": "BLOCKED", "blockers": [SOURCE], "full_rom_rebuild_tested": False,
        })
        self.assertNotIn("manifests/martini.xml", json.dumps(profile))

    def check_derivation(self, baseline):
        derived = baseline["derived_from"]
        raw = self.required_file(baseline["manifest"]["portable"]["path"]).read_bytes()
        self.assertEqual(baseline["manifest"]["portable"]["bytes"], len(raw))
        self.assertEqual(baseline["manifest"]["portable"]["sha256"], sha256(raw))
        old = ET.fromstring(self.required_file(derived["manifest"]).read_bytes())
        new = ET.fromstring(raw)
        self.assertEqual([element_record(e) for e in new if e.tag != "project"],
                         [element_record(e) for e in old if e.tag != "project"])
        ops = derived["operations"]
        added = {o["path"] for o in ops if o["operation"] == "add_project"}
        replaced = {o["path"]: o["attributes"] for o in ops if o["operation"] == "replace_project"}
        deepen = any(o["operation"] == "add_clone_depth" for o in ops)
        old_projects = {p.get("path", p.get("name")): p for p in old.findall("project")}
        new_projects = {p.get("path", p.get("name")): p for p in new.findall("project")}
        self.assertEqual(set(new_projects) - set(old_projects), added)
        self.assertEqual(set(old_projects) - set(new_projects), set())
        self.assertEqual(baseline["manifest"]["project_count"], len(new_projects))
        deepened = revisions_changed = 0
        for path, before in old_projects.items():
            after = copy.deepcopy(new_projects[path])
            if path in replaced:
                for key, value in replaced[path].items():
                    self.assertEqual(after.get(key), value, path)
                    after.set(key, before.get(key))
                revisions_changed += before.get("revision") != replaced[path].get("revision", before.get("revision"))
            elif deepen and after.get("clone-depth") != before.get("clone-depth"):
                # Only Evolution-X projects, never the mirror-served SettingsGoogle.
                self.assertEqual((before.get("remote"), after.get("clone-depth")), ("evo", "1"), path)
                self.assertNotEqual(path, "vendor/google/apps/SettingsGoogle")
                del after.attrib["clone-depth"]
                deepened += 1
            self.assertEqual(element_record(after), element_record(before), path)
        if deepen:
            self.assertEqual(deepened, next(o["count"] for o in ops if o["operation"] == "add_clone_depth"))
        self.assertEqual(bool(revisions_changed), derived["revisions_changed"])

    def test_derived_locks_only_apply_documented_operations(self):
        derived = [path for path in sorted((ROOT / "baselines").glob("*.json"))
                   if "derived_from" in json.loads(path.read_text())]
        self.assertIn(ROOT / ACTIVE_BASELINE, derived)
        for path in derived:
            with self.subTest(baseline=path.name):
                self.check_derivation(json.loads(path.read_text()))

    def test_ksu_sources_in_active_lock(self):
        projects = {p.get("path", p.get("name")): p for p in
                    ET.fromstring(self.required_file(ACTIVE_MANIFEST).read_bytes()).findall("project")}
        kernel, ksu = projects["kernel/oneplus/sm8350"], projects[KSU_KERNEL]
        self.assertEqual((ksu.get("name"), ksu.get("revision")), (kernel.get("name"), kernel.get("revision")))
        source = projects[KSU_SOURCE]
        self.assertEqual((source.get("revision"), source.get("upstream")), (KSU_REVISION, "refs/heads/legacy"))
        # Kbuild runs "git fetch --unshallow" on shallow checkouts; keep the full history.
        self.assertIsNone(source.get("clone-depth"))
        variant = self.load_json(ACTIVE_BASELINE)["kernel"]["variants"]["ksu"]
        self.assertEqual((variant["repo"], variant["kernelsu_next"]["revision"]), (KSU_KERNEL, KSU_REVISION))

    def test_source_descriptor_is_explicitly_external_and_blocked(self):
        source = self.load_json(SOURCE)
        self.assertEqual(source["status"], "BLOCKED")
        self.assertEqual(source["status_scope"], "independent-public-recovery")
        self.assertEqual(source["repo"], "vendor/google/apps/SettingsGoogle")
        self.assertEqual(source["base_revision"], HEADS[source["repo"]])
        self.assertEqual(source["corrected_reference_revision"], CORRECTED)
        self.assertEqual(source["upstream_repository"], "https://github.com/Evolution-X/vendor_google_apps_SettingsGoogle")
        self.assertEqual(source["upstream_availability"], "not-checked-offline")
        self.assertEqual(source["external_inputs"], {
            "settings_google_bundle": {
                "type": "git-bundle", "argument": "--source-bundle",
                "filename": "SettingsGoogle-86a6033a-f38977d0.bundle",
                "bytes": BUNDLE_BYTES, "sha256": BUNDLE_SHA, "included": False,
                "repository_path": None, "download_url": None,
            },
            "settings_google_patch": {
                "type": "git-diff", "argument": "--settings-patch",
                "filename": "0001-fix-screen-collector.patch",
                "bytes": SETTINGS_PATCH_BYTES, "sha256": PATCHES[2][3], "included": False,
                "repository_path": None, "download_url": None,
                "historical_source": HISTORICAL_SETTINGS_PATCH,
            },
        })
        self.assertEqual(source["local_recovery"], {
            "status": "REQUIRES_EXPLICIT_INPUTS",
            "required_inputs": ["settings_google_bundle", "settings_google_patch"],
            "validation_is_distribution_permission": False,
        })
        self.assertEqual(source["validation"]["scope"], "historical-offline-verification-not-a-test-entrypoint")
        self.assertIs(source["validation"]["implicit_host_lookup"], False)
        self.assertNotIn("command", source["validation"])
        self.assertFalse(list((ROOT / "sources").rglob("*.bundle")))

    def test_new_json_is_host_independent(self):
        for relative in (BASELINE, "baselines/20261001.json", ACTIVE_BASELINE,
                         "profiles/martini.json", SERIES, SOURCE):
            text = self.required_file(relative).read_text()
            self.load_json(relative)
            self.assertNotRegex(text, r"/(?:home|Users|tmp|mnt)/")
            self.assertNotIn("file://", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
