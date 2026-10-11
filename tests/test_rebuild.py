# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline functional tests; tiny Git repositories, never Android sync/build."""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET


CONTROL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rebuild", CONTROL / "tools/rebuild.py")
rebuild = importlib.util.module_from_spec(SPEC)
if SPEC.loader and Path(SPEC.origin).exists():
    SPEC.loader.exec_module(rebuild)


def fingerprint(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def git(path, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TEMPLATE_DIR="")
    return subprocess.check_output(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(path), *args],
        env=env, stderr=subprocess.PIPE,
    )


class RebuildTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(hasattr(rebuild, "Rebuild"), "tools/rebuild.py must implement Rebuild")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.control = self.root / "control"
        self.source = self.root / "source"
        self.control.mkdir()
        self.source.mkdir()
        self.patch = self.root / "settings.patch"
        self.heads = {}
        entries = []
        for name in ("first", "settings"):
            repo = self.source / name
            repo.mkdir()
            git(repo, "init", "--quiet")
            (repo / "tracked").write_text("before\n")
            git(repo, "add", "tracked")
            git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "--quiet", "-m", "synthetic baseline\n\nCo-Authored-By: Claude Code <noreply@anthropic.com>")
            self.heads[name] = git(repo, "rev-parse", "HEAD").decode().strip()
            patch = ("diff --git a/tracked b/tracked\n--- a/tracked\n+++ b/tracked\n"
                     "@@ -1 +1 @@\n-before\n+after\n")
            if name == "first":
                patch += ("diff --git a/new-file b/new-file\nnew file mode 100644\n"
                          "--- /dev/null\n+++ b/new-file\n@@ -0,0 +1 @@\n+created\n"
                          # Like drivers/kernelsu: a symlink leaving the project.
                          "diff --git a/sub/outside-link b/sub/outside-link\nnew file mode 120000\n"
                          "--- /dev/null\n+++ b/sub/outside-link\n@@ -0,0 +1 @@\n"
                          "+../../settings\n\\ No newline at end of file\n")
            path = self.control / "patches/first.patch" if name == "first" else self.patch
            path.parent.mkdir(exist_ok=True)
            path.write_text(patch)
            entry = {"id": name, "repo": name, "base_revision": self.heads[name],
                     **fingerprint(path)}
            entry.update({"patch": "patches/first.patch"} if name == "first" else
                         {"external_input": "settings_google_patch"})
            entries.append(entry)
        self.profile = {
            "baseline": "baselines/base.json", "manifest": "manifests/locked/test.xml",
            "patch_series": "patches/series.json", "source_restores": ["sources/settings-google.json"],
            "lunch": "lineage_martini-cp2a-userdebug",
            "environment": {"EVO_KEEP_TARGET_FILES": "true"},
            "kernel_variants": {"normal": {"environment": {}, "target": "evolution"},
                                "ksu": {"environment": {"MARTINI_KSU": "true"}, "target": "bootimage"}},
        }
        manifest = ET.Element("manifest")
        for name, head in self.heads.items():
            ET.SubElement(manifest, "project", name=name, path=name,
                          revision=head, upstream="refs/heads/cnb")
        manifest_path = self.control / self.profile["manifest"]
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_bytes(ET.tostring(manifest))
        self.series = {"patches": entries}
        self.restore = {
            "repo": "settings", "base_revision": self.heads["settings"],
            "external_inputs": {"settings_google_patch": fingerprint(self.patch)},
        }
        write_json(self.control / "profiles/martini.json", self.profile)
        write_json(self.control / "baselines/base.json", {
            "repo_heads": self.heads, "manifest": {"portable": fingerprint(manifest_path)},
        })
        write_json(self.control / "patches/series.json", self.series)
        write_json(self.control / "sources/settings-google.json", self.restore)
        (self.control / "certificates").mkdir()
        for name in ("release-info.json", "martini-release.x509.pem"):
            shutil.copyfile(CONTROL / "certificates" / name, self.control / "certificates" / name)
        git(self.control, "init", "--quiet")
        self.commit_control()

    def commit_control(self):
        git(self.control, "add", ".")
        git(self.control, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "--quiet", "-m", "synthetic control inputs\n\nCo-Authored-By: Claude Code <noreply@anthropic.com>")

    def workspace(self, **kwargs):
        return rebuild.Rebuild(self.control, self.source, settings_patch=self.patch, **kwargs)

    def test_prepare_applies_grouped_diffs_without_committing(self):
        # Deliberately inherited Git redirection must not redirect our Git commands.
        with mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent/host.git",
                                          "GIT_CONFIG_COUNT": "99"}):
            work = self.workspace()
            work.prepare()
            work.check_prepared()
        for name, head in self.heads.items():
            self.assertEqual((self.source / name / "tracked").read_text(), "after\n")
            self.assertEqual(git(self.source / name, "rev-parse", "HEAD").decode().strip(), head)
            self.assertEqual(git(self.source / name, "diff", "--cached"), b"")
        record = json.loads((self.source / ".martini-prepared.json").read_text())
        self.assertIn("new-file", record["repositories"]["first"]["untracked"])
        with self.assertRaises(rebuild.RebuildError):
            work.prepare()

    def test_invalid_patch_base_or_dirty_tree_refuses_before_applying_anything(self):
        for case in ("hash", "size", "base", "dirty", "apply-check"):
            with self.subTest(case=case):
                series = copy.deepcopy(self.series)
                patch_before = self.patch.read_bytes()
                settings = self.source / "settings"
                if case == "hash":
                    series["patches"][-1]["sha256"] = "0" * 64
                elif case == "size":
                    series["patches"][-1]["bytes"] += 1
                elif case == "base":
                    series["patches"][-1]["base_revision"] = "0" * 40
                elif case == "dirty":
                    (settings / "unexpected").write_text("unknown\n")
                else:
                    self.patch.write_bytes(patch_before.replace(b"-before", b"-not-the-base"))
                    series["patches"][-1].update(fingerprint(self.patch))
                    restore = copy.deepcopy(self.restore)
                    restore["external_inputs"]["settings_google_patch"] = fingerprint(self.patch)
                    write_json(self.control / "sources/settings-google.json", restore)
                write_json(self.control / "patches/series.json", series)
                before = {p.relative_to(self.source): p.read_bytes()
                          for p in self.source.rglob("*") if p.is_file()}
                with self.assertRaises((rebuild.RebuildError, subprocess.CalledProcessError)):
                    self.workspace().prepare()
                after = {p.relative_to(self.source): p.read_bytes()
                         for p in self.source.rglob("*") if p.is_file()}
                self.assertEqual(after, before)
                self.patch.write_bytes(patch_before)
                (settings / "unexpected").unlink(missing_ok=True)
                write_json(self.control / "sources/settings-google.json", self.restore)
        write_json(self.control / "patches/series.json", self.series)

    def test_prepared_record_detects_content_and_input_drift_not_document_commits(self):
        work = self.workspace()
        work.prepare()
        (self.control / "README.md").write_text("Documentation-only change\n")
        self.commit_control()
        work.check_prepared()
        for path in (self.source / "first/tracked", self.source / "first/new-file",
                     self.control / "profiles/martini.json"):
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(path=path), self.assertRaises(rebuild.RebuildError):
                self.workspace().check_prepared()
            path.write_bytes(original)
        work.check_prepared()

    def test_dry_run_all_commands_has_no_subprocess_or_filesystem_writes(self):
        missing = self.root / "not-created"
        before = sorted(str(p) for p in self.root.rglob("*"))
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess")), \
             mock.patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            for command in ("init", "adopt", "prepare", "build", "update"):
                self.assertEqual(rebuild.main(
                    [command, "--source", str(missing), "--dry-run"], control=self.control), 0)
        self.assertIn("BUILT_AND_ARCHIVED_UNVALIDATED", output.getvalue())
        self.assertEqual(sorted(str(p) for p in self.root.rglob("*")), before)

    @unittest.skipUnless(shutil.which("openssl"), "public certificate parsing needs openssl")
    def test_build_failure_exit_code_survives_logging(self):
        work = self.workspace()
        work.prepare()
        keys = self.source / "vendor/evolution-priv/keys"
        keys.mkdir(parents=True)
        shutil.copyfile(self.control / "certificates/martini-release.x509.pem", keys / "testkey.x509.pem")
        (keys / "testkey.pk8").write_bytes(b"fixture placeholder; never parsed or printed")
        envsetup = self.source / "build/envsetup.sh"
        envsetup.parent.mkdir()
        envsetup.write_text(
            'lunch() { return 0; }\n'
            'get_build_var() {\n'
            ' case "$1" in\n'
            ' DEFAULT_SYSTEM_DEV_CERTIFICATE) printf "%s\\n" vendor/evolution-priv/keys/testkey;;\n'
            ' LINEAGE_VERSION) printf "%s\\n" synthetic-build;;\n'
            ' esac\n}\n'
            'm() { printf "synthetic build failed\\n"; return 23; }\n')
        manifest = (self.control / self.profile["manifest"]).read_bytes()
        with mock.patch.object(rebuild.Rebuild, "check_source", return_value=manifest), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = rebuild.main(["build", "--source", str(self.source),
                                 "--settings-patch", str(self.patch)], control=self.control)
        self.assertEqual(code, 23)
        runs = list((self.source / "artifacts").iterdir())
        self.assertEqual(len(runs), 1)
        result = json.loads((runs[0] / "result.json").read_text())
        self.assertEqual(result["exit_code"], 23)
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("synthetic build failed", (runs[0] / "build.log").read_text())
        self.assertFalse(list(runs[0].glob("*.zip")))

    def fake_android_build(self):
        keys = self.source / "vendor/evolution-priv/keys"
        keys.mkdir(parents=True)
        shutil.copyfile(self.control / "certificates/martini-release.x509.pem", keys / "testkey.x509.pem")
        (keys / "testkey.pk8").write_bytes(b"fixture placeholder; never parsed or printed")
        envsetup = self.source / "build/envsetup.sh"
        envsetup.parent.mkdir()
        envsetup.write_text(
            'lunch() { return 0; }\n'
            'get_build_var() {\n'
            ' case "$1" in\n'
            ' DEFAULT_SYSTEM_DEV_CERTIFICATE) printf "%s\\n" vendor/evolution-priv/keys/testkey;;\n'
            ' LINEAGE_VERSION) printf "%s\\n" synthetic-build;;\n'
            ' esac\n}\n'
            'm() {\n'
            ' printf "MARTINI_KSU=%s target=%s OUT_DIR=%s\\n" "${MARTINI_KSU-unset}" "$1" "$OUT_DIR"\n'
            ' [ -n "$FAKE_BOOT_OK" ] || return 23\n'
            ' mkdir -p "$OUT_DIR/target/product/martini"\n'
            ' printf boot > "$OUT_DIR/target/product/martini/boot.img"\n}\n')
        return (self.control / self.profile["manifest"]).read_bytes()

    @unittest.skipUnless(shutil.which("openssl"), "public certificate parsing needs openssl")
    def test_kernel_variant_sets_environment_and_owns_its_out(self):
        self.workspace().prepare()
        manifest = self.fake_android_build()
        out = self.source / "out-ksu"

        def build(kernel):
            with mock.patch.object(rebuild.Rebuild, "check_source", return_value=manifest), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return rebuild.main(["build", "--source", str(self.source), "--kernel", kernel,
                                     "--out", str(out), "--settings-patch", str(self.patch)],
                                    control=self.control)

        self.assertEqual(build("ksu"), 23)
        run = next((self.source / "artifacts").iterdir())
        self.assertIn("MARTINI_KSU=true target=bootimage OUT_DIR=out-ksu", (run / "build.log").read_text())
        self.assertEqual(json.loads((run / "result.json").read_text())["kernel"], "ksu")
        # A normal build must not reuse (and silently mix into) the KSU OUT.
        self.assertEqual(build("normal"), 1)
        self.assertEqual(len(list((self.source / "artifacts").iterdir())), 1)
        self.assertEqual(build("unknown"), 1)
        self.assertEqual(rebuild.main(["build", "--source", str(self.source), "--kernel", "ksu",
                                       "--out", str(self.root / "outside")], control=self.control), 1)
        # A successful KSU variant archives only its boot.img, named after the ROM version.
        with mock.patch.dict(os.environ, {"FAKE_BOOT_OK": "1"}):
            self.assertEqual(build("ksu"), 0)
        result = [json.loads(r.read_text()) for r in (self.source / "artifacts").glob("*/result.json")]
        done = [r for r in result if r["status"] == "BUILT_AND_ARCHIVED_UNVALIDATED"]
        self.assertEqual([list(r["artifacts"]) for r in done], [["synthetic-build-ksu-boot.img"]])

    def test_update_undoes_only_recorded_changes_before_resync(self):
        self.workspace().prepare()
        self.profile["source_restores"] = []
        write_json(self.control / "profiles/martini.json", self.profile)
        stale = self.source / ".repo/local_manifests/martini-settings.xml"
        stale.parent.mkdir(parents=True)
        stale.write_text("<manifest/>")
        self.series["patches"] = self.series["patches"][:1]
        write_json(self.control / "patches/series.json", self.series)
        self.commit_control()
        commit = git(self.control, "rev-parse", "HEAD").decode().strip()
        unknown = self.source / "first/unknown"
        unknown.write_text("not ours\n")
        original_run = rebuild.run
        calls = []

        def repo_recorded(command, **kwargs):
            if command[0] != "repo":
                return original_run(command, **kwargs)
            calls.append(command)
            return b""

        with mock.patch.object(rebuild, "run", side_effect=repo_recorded):
            with self.assertRaises(rebuild.RebuildError):
                self.workspace().update()
        self.assertEqual(calls, [])
        self.assertEqual((self.source / "first/tracked").read_text(), "after\n")
        unknown.unlink()
        with mock.patch.object(rebuild, "run", side_effect=repo_recorded), \
             contextlib.redirect_stdout(io.StringIO()):
            self.workspace(clone_depth=1).update()
        self.assertEqual([c[:2] for c in calls], [["repo", "init"], ["repo", "sync"]])
        self.assertIn(commit, calls[0])
        self.assertIn("--depth=1", calls[0])
        for name in self.heads:
            self.assertEqual(git(self.source / name, "status", "--porcelain"), b"")
        self.assertFalse((self.source / "first/sub").exists())
        self.assertTrue((self.source / "settings/tracked").is_file())
        self.assertFalse((self.source / ".martini-prepared.json").exists())
        self.assertEqual(len(list((self.source / ".martini-history").iterdir())), 1)
        self.assertFalse(stale.exists())
        self.workspace().prepare()

    def test_adopt_moves_only_clean_checkouts_of_replaced_projects(self):
        snapshot = ET.Element("manifest")
        ET.SubElement(snapshot, "project", name="base/first", path="first")
        ET.SubElement(snapshot, "project", name="settings", path="settings")
        ET.SubElement(snapshot, "project", name="base/only", path="only")
        # A replaced project whose earlier sync failed: no checkout, only a Git dir.
        ET.SubElement(snapshot, "project", name="base/missing", path="missing")
        self.locked_extra = ET.parse(self.control / self.profile["manifest"])
        ET.SubElement(self.locked_extra.getroot(), "project", name="missing", path="missing",
                      revision="0" * 40)
        self.locked_extra.write(self.control / self.profile["manifest"])
        (self.source / ".repo/projects/missing.git").mkdir(parents=True)
        gitdir = self.source / ".repo/projects/first.git"
        gitdir.mkdir(parents=True)
        original_run = rebuild.run

        def snapshot_manifest(command, **kwargs):
            if command[:2] == ["repo", "manifest"]:
                return ET.tostring(snapshot)
            return original_run(command, **kwargs)

        (self.source / "first/tracked").write_text("local change\n")
        with mock.patch.object(rebuild, "run", side_effect=snapshot_manifest):
            with self.assertRaises(rebuild.RebuildError):
                self.workspace().adopt()
            self.assertTrue((self.source / "first/tracked").is_file())
            git(self.source / "first", "checkout", "--", "tracked")
            with contextlib.redirect_stdout(io.StringIO()):
                self.workspace().adopt()
        [moved] = (self.source / ".martini-displaced").iterdir()
        self.assertEqual((moved / "tree/first/tracked").read_text(), "before\n")
        self.assertTrue((moved / "projects/first.git").is_dir())
        self.assertTrue((moved / "projects/missing.git").is_dir())
        self.assertFalse((self.source / "first").exists() or gitdir.exists())
        self.assertTrue((self.source / "settings/tracked").is_file())
        (self.source / ".martini-history").mkdir()
        with self.assertRaises(rebuild.RebuildError):
            self.workspace().adopt()

    def hook(self, repo, name):
        # What crave's accelerator does to a compiler: original kept as untracked mbt-bin-NAME.
        os.rename(repo / name, repo / ("mbt-bin-" + name))
        (repo / name).write_text("crave hook\n")

    def test_crave_hooks_are_accepted_only_in_crave_mode_and_undone_where_sync_moves(self):
        gone = self.source / "gone"
        gone.mkdir()
        git(gone, "init", "--quiet")
        (gone / "gcc").write_text("compiler\n")
        (gone / "kernel-gcc").symlink_to("gcc")
        git(gone, "add", ".")
        git(gone, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "--quiet", "-m", "synthetic prebuilt\n\nCo-Authored-By: Claude Code <noreply@anthropic.com>")
        for repo, name in ((self.source / "first", "tracked"), (gone, "gcc"), (gone, "kernel-gcc")):
            self.hook(repo, name)
        with self.assertRaises(rebuild.RebuildError):
            self.workspace().clean(gone, hooks=True)
        crave = self.workspace(crave=True)
        crave.clean(gone, hooks=True)
        with self.assertRaises(rebuild.RebuildError):
            crave.clean(gone)
        (gone / "stray").write_text("not a hook\n")
        with self.assertRaises(rebuild.RebuildError):
            crave.clean(gone, hooks=True)
        (gone / "stray").unlink()
        # "first" stays at its locked revision and keeps its hook; "gone" leaves the lock.
        snapshot = ET.Element("manifest")
        for name in ("first", "settings"):
            ET.SubElement(snapshot, "project", name=name, path=name)
        # An earlier failed sync already switched manifests; Repo still lists "gone" for removal.
        (self.source / ".repo").mkdir()
        (self.source / ".repo/project.list").write_text("first\ngone\nsettings\n")
        original_run = rebuild.run

        def snapshot_manifest(command, **kwargs):
            if command[:2] == ["repo", "manifest"]:
                return ET.tostring(snapshot)
            return original_run(command, **kwargs)

        with mock.patch.object(rebuild, "run", side_effect=snapshot_manifest), \
             contextlib.redirect_stdout(io.StringIO()):
            crave.unhook_moving()
        self.assertEqual(git(gone, "status", "--porcelain"), b"")
        self.assertTrue((gone / "kernel-gcc").is_symlink())
        self.assertEqual((self.source / "first/tracked").read_text(), "crave hook\n")
        self.assertTrue((self.source / "first/mbt-bin-tracked").is_file())

    def test_build_refuses_uncommitted_control_before_source_work(self):
        work = self.workspace()
        (self.control / "README.md").write_text("uncommitted control change\n")
        with mock.patch.object(work, "check_source", side_effect=rebuild.RebuildError("source reached")) as source:
            with self.assertRaises(rebuild.RebuildError):
                work.build()
            source.assert_not_called()
        self.assertFalse((self.source / "artifacts").exists())

    def test_init_refuses_existing_tree_without_running_commands(self):
        before = sorted(str(p) for p in self.source.rglob("*"))
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess")):
            with self.assertRaises(rebuild.RebuildError):
                self.workspace().init()
        self.assertEqual(sorted(str(p) for p in self.source.rglob("*")), before)

    def test_init_recovers_manifest_upstream_in_private_mirror_before_sync(self):
        bundle = self.root / "authorized-synthetic.bundle"
        git(self.source / "settings", "bundle", "create", str(bundle), "--all")
        bundle_before = fingerprint(bundle)
        self.restore["external_inputs"]["settings_google_bundle"] = bundle_before
        write_json(self.control / "sources/settings-google.json", self.restore)
        self.commit_control()
        new_source = self.root / "fresh-source"
        work = rebuild.Rebuild(self.control, new_source, source_bundle=bundle)
        original_run = rebuild.run
        calls = []

        def local_only(command, **kwargs):
            if command[0] != "repo":
                return original_run(command, **kwargs)
            calls.append(command)
            if command[1] == "init":
                (new_source / ".repo").mkdir()
            else:
                local = ET.parse(new_source / ".repo/local_manifests/martini-settings.xml").getroot()
                override = local.find("extend-project")
                self.assertEqual(override.get("path"), "settings")
                self.assertIsNone(override.get("revision"))
                mirror = new_source / ".martini-cache/settings.git"
                self.assertEqual(git(mirror, "rev-parse", "refs/heads/cnb").decode().strip(),
                                 self.heads["settings"])
                self.assertEqual(local.find("remote").get("fetch"), mirror.parent.as_uri())
            return b""

        with mock.patch.object(rebuild, "run", side_effect=local_only):
            work.init()
        self.assertEqual([c[1] for c in calls], ["init", "sync"])
        self.assertIn("--git-lfs", calls[0])
        self.assertEqual(fingerprint(bundle), bundle_before)

    def test_init_without_source_restore_needs_no_bundle(self):
        self.profile["source_restores"] = []
        write_json(self.control / "profiles/martini.json", self.profile)
        self.series["patches"] = self.series["patches"][:1]
        write_json(self.control / "patches/series.json", self.series)
        self.commit_control()
        new_source = self.root / "fresh-source"
        calls, original_run = [], rebuild.run

        def repo_only(command, **kwargs):
            if command[0] != "repo":
                return original_run(command, **kwargs)
            calls.append(command)
            return b""

        with mock.patch.object(rebuild, "run", side_effect=repo_only), \
             contextlib.redirect_stdout(io.StringIO()):
            rebuild.Rebuild(self.control, new_source).init()
        self.assertEqual([c[:2] for c in calls], [["repo", "init"], ["repo", "sync"]])
        self.assertFalse((new_source / ".martini-cache").exists())
        # Without the external entry, prepare needs no --settings-patch either.
        rebuild.Rebuild(self.control, self.source).patches()

    def test_build_source_mapping_rejects_changed_revision(self):
        self.workspace().prepare()
        manifest = ET.parse(self.control / self.profile["manifest"])
        manifest.getroot().find("project").set("revision", "0" * 40)
        original_run = rebuild.run

        def manifest_only(command, **kwargs):
            if command[:3] == ["repo", "manifest", "-r"]:
                return ET.tostring(manifest.getroot())
            return original_run(command, **kwargs)

        with mock.patch.object(rebuild, "run", side_effect=manifest_only):
            with self.assertRaises(rebuild.RebuildError):
                self.workspace().check_source()
        self.assertFalse((self.source / "artifacts").exists())


if __name__ == "__main__":
    unittest.main()
