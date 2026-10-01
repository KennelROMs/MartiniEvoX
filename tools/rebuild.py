#!/usr/bin/env python3
# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
"""Rebuild the pinned martini ROM (normal or KSU kernel); no flashing or validation claims."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


CONTROL = Path(__file__).resolve().parents[1]
PREPARED = ".martini-prepared.json"
OUT_KERNEL = ".martini-kernel"


class RebuildError(Exception):
    pass


def environment():
    # Never inherit another checkout's Git location, object store or injected config.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GIT_", "BASH_FUNC_"))
           and k not in ("BASH_ENV", "ENV", "OUT_DIR_COMMON_BASE")}
    # Keep normal user/system configuration: Repo identity and installed LFS filters need it.
    env.update(GIT_TEMPLATE_DIR="", GIT_OPTIONAL_LOCKS="0")
    return env


def run(command, *, cwd=None, input=None, stdout=subprocess.PIPE, env=None):
    return subprocess.run(
        [str(arg) for arg in command], cwd=cwd, input=input,
        env=environment() if env is None else env, stdout=stdout,
        stderr=subprocess.PIPE if stdout == subprocess.PIPE else subprocess.STDOUT,
        check=True,
    ).stdout


def git(repo, *args, input=None):
    return run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                "-C", repo, *args], input=input)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def verify_file(path, expected):
    actual = fingerprint(path)
    if any(actual[key] != expected[key] for key in ("sha256", "bytes") if key in expected):
        raise RebuildError(f"Input size/SHA256 mismatch: {path}")
    return actual


def inside(path, parent):
    return path == parent or parent in path.parents


def child(root, relative):
    path = (root / relative).resolve()
    if not inside(path, root) or path == root:
        raise RebuildError(f"Expected a path inside {root}: {relative}")
    return path


def projects(xml):
    result = {}
    for project in ET.fromstring(xml).findall("project"):
        path = project.get("path", project.get("name"))
        if path in result:
            raise RebuildError(f"Duplicate manifest project path: {path}")
        result[path] = project.attrib
    return result


@contextmanager
def workspace_lock(source):
    # Linux directory flock: one workspace lock, with no lock-file side effects.
    descriptor = os.open(source, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RebuildError(f"Workspace is busy: {source}") from exc
        yield
    finally:
        os.close(descriptor)


class Rebuild:
    def __init__(self, control, source, *, source_bundle=None, settings_patch=None,
                 out=None, artifacts=None, signing="self-build", kernel="normal"):
        self.control = Path(control).resolve()
        for path in (source, out, artifacts):
            if path is not None and not Path(path).is_absolute():
                raise RebuildError(f"SOURCE/OUT/ARTIFACTS must be absolute: {path}")
        self.source = Path(source).resolve()
        self.out = Path(out).resolve() if out else self.source / "out"
        self.artifacts = Path(artifacts).resolve() if artifacts else self.source / "artifacts"
        for path in (self.source, self.out, self.artifacts):
            if inside(path, self.control) or inside(self.control, path):
                raise RebuildError("SOURCE/OUT/ARTIFACTS must be separate from CONTROL")
        if (inside(self.source, self.out) or inside(self.source, self.artifacts)
                or inside(self.artifacts, self.out) or inside(self.out, self.artifacts)):
            raise RebuildError("OUT and ARTIFACTS must not overlap each other or contain SOURCE")
        if not inside(self.out, self.source):
            # Siso only loads its generated config through an OUT_DIR relative to SOURCE.
            raise RebuildError(f"OUT must be inside SOURCE (e.g. SOURCE/out-ksu): {self.out}")
        self.bundle = Path(source_bundle).resolve() if source_bundle else None
        self.settings_patch = Path(settings_patch).resolve() if settings_patch else None
        self.signing = signing
        self.kernel = kernel
        self.profile = read_json(self.control / "profiles/martini.json")
        self.baseline = read_json(child(self.control, self.profile["baseline"]))
        self.series = read_json(child(self.control, self.profile["patch_series"]))
        # Optional external source restore (the historical SettingsGoogle bundle).
        restores = self.profile.get("source_restores", [])
        self.restore_path = restores[0] if restores else None
        self.restore = read_json(child(self.control, self.restore_path)) if restores else None
        self.manifest = child(self.control, self.profile["manifest"])
        self.locked = projects(self.manifest.read_bytes())
        if (self.profile["lunch"] != "lineage_martini-cp2a-userdebug"
                or self.profile["kernel_variants"]["normal"]["target"] != "evolution"
                or self.profile["environment"].get("EVO_KEEP_TARGET_FILES") != "true"):
            raise RebuildError("Only the pinned martini profile is supported")
        if kernel not in self.profile["kernel_variants"]:
            raise RebuildError(f"Unknown kernel variant: {kernel}")

    def patches(self):
        patches = []
        for entry in self.series["patches"]:
            if "external_input" in entry:
                if (entry["external_input"] != "settings_google_patch" or not self.settings_patch
                        or not self.restore):
                    raise RebuildError("prepare/build require explicit --settings-patch FILE")
                path = self.settings_patch
                verify_file(path, self.restore["external_inputs"]["settings_google_patch"])
                if (entry["repo"] != self.restore["repo"]
                        or entry["base_revision"] != self.restore["base_revision"]):
                    raise RebuildError("Settings descriptor and patch baseline disagree")
            else:
                path = child(self.control, entry["patch"])
            verify_file(path, entry)
            if (entry["base_revision"] != self.baseline["repo_heads"][entry["repo"]]
                    or entry["base_revision"] != self.locked[entry["repo"]]["revision"]):
                raise RebuildError(f"Patch/manifest/baseline disagree: {entry['repo']}")
            patches.append((entry, path))
        return patches

    def input_hashes(self):
        verify_file(self.manifest, self.baseline["manifest"]["portable"])
        paths = ["profiles/martini.json", self.profile["baseline"], self.profile["manifest"],
                 self.profile["patch_series"], "certificates/release-info.json"]
        if self.restore_path:
            paths.append(self.restore_path)
        inputs = {path: fingerprint(child(self.control, path)) for path in paths}
        inputs["tools/rebuild.py"] = fingerprint(Path(__file__).resolve())
        for entry, path in self.patches():
            # Internal entries pin SHA256; external entries additionally pin byte count.
            inputs["patch:" + entry["id"]] = fingerprint(path)
        return inputs

    def clean(self, repo):
        if Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve() != repo:
            raise RebuildError(f"Not an independent source project: {repo}")
        if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
            raise RebuildError(f"Dirty or already-patched project; inspect without resetting: {repo}")

    def snapshot(self, repo):
        untracked = {}
        for name in git(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
            if not name:
                continue
            name = os.fsdecode(name)
            path = repo / name
            if path.is_symlink():
                content = os.fsencode(os.readlink(path))
                info = {"sha256": hashlib.sha256(content).hexdigest(), "symlink": True}
            else:
                info = fingerprint(path)
            info["mode"] = path.lstat().st_mode
            untracked[name] = info
        diff = git(repo, "diff", "HEAD", "--binary", "--no-ext-diff", "--no-textconv", "--no-renames")
        return {"head": git(repo, "rev-parse", "HEAD").decode().strip(),
                "diff_sha256": hashlib.sha256(diff).hexdigest(), "untracked": untracked}

    def init(self):
        if self.source.exists() and (not self.source.is_dir() or any(self.source.iterdir())):
            raise RebuildError("init only accepts a nonexistent or empty SOURCE")
        self.clean(self.control)
        commit = git(self.control, "rev-parse", "HEAD").decode().strip()
        verify_file(self.manifest, self.baseline["manifest"]["portable"])
        if self.restore:
            if not self.bundle:
                raise RebuildError("init requires explicit --source-bundle FILE from an authorized holder")
            verify_file(self.bundle, self.restore["external_inputs"]["settings_google_bundle"])
            project = self.locked[self.restore["repo"]]
            base, upstream = project["revision"], project["upstream"]
            if base != self.restore["base_revision"] or not upstream.startswith("refs/heads/"):
                raise RebuildError("Settings base/upstream is not the expected pinned branch")
        self.source.mkdir(parents=True, exist_ok=True, mode=0o700)
        with workspace_lock(self.source):
            if any(self.source.iterdir()):
                raise RebuildError("SOURCE became nonempty; refusing init")
            if self.restore:
                cache = self.source / ".martini-cache"
                cache.mkdir(mode=0o700)
                mirror = child(cache, project["name"] + ".git")
                mirror.parent.mkdir(parents=True, exist_ok=True)
                run(["git", "-c", "core.hooksPath=/dev/null", "clone", "--mirror", "--template=",
                     self.bundle, mirror])
                git(mirror, "cat-file", "-e", base + "^{commit}")
                git(mirror, "update-ref", upstream, base)
            run(["repo", "init", "-u", self.control, "-b", commit, "-m",
                 self.profile["manifest"], "--git-lfs"], cwd=self.source, stdout=None)
            if self.restore:
                self.install_settings_mirror(cache, project)
            run(["repo", "sync", "-c", "--no-clone-bundle", "--no-tags"],
                cwd=self.source, stdout=None)
        print(f"Initialized pinned SOURCE: {self.source}")

    def install_settings_mirror(self, cache, project):
        local = ET.Element("manifest")
        ET.SubElement(local, "remote", name="martini-settings-local", fetch=cache.as_uri())
        ET.SubElement(local, "extend-project", name=project["name"], path=self.restore["repo"],
                      remote="martini-settings-local")
        directory = self.source / ".repo/local_manifests"
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "martini-settings.xml").open("xb") as stream:
            stream.write(ET.tostring(local, encoding="utf-8", xml_declaration=True))

    def update(self):
        # Move a prepared SOURCE to the current CONTROL commit. Only changes proven
        # identical to our own preparation record are undone; anything else stops.
        with workspace_lock(self.source):
            self.clean(self.control)
            commit = git(self.control, "rev-parse", "HEAD").decode().strip()
            record_path = self.source / PREPARED
            if record_path.exists():
                record = read_json(record_path)
                for name, previous in record["repositories"].items():
                    if self.snapshot(child(self.source, name)) != previous:
                        raise RebuildError(f"Prepared worktree changed; inspect manually: {name}")
                for name, previous in record["repositories"].items():
                    repo = child(self.source, name)
                    git(repo, "checkout", "--quiet", "--", ".")
                    for relative in previous["untracked"]:
                        # Recorded names are Git paths; do not follow a symlink they may name.
                        if ".." in Path(relative).parts or Path(relative).is_absolute():
                            raise RebuildError(f"Unexpected recorded path: {relative}")
                        path = repo / relative
                        path.unlink()
                        parent = path.parent
                        while parent != repo and not any(parent.iterdir()):
                            parent.rmdir()
                            parent = parent.parent
                    self.clean(repo)
                history = self.source / ".martini-history"
                history.mkdir(exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                record_path.rename(history / f"prepared-{stamp}.json")
            settings = self.source / ".repo/local_manifests/martini-settings.xml"
            if not self.restore and settings.exists():
                # Written by an earlier init with the SettingsGoogle restore; no longer used.
                settings.unlink()
            run(["repo", "init", "-u", self.control, "-b", commit, "-m",
                 self.profile["manifest"], "--git-lfs"], cwd=self.source, stdout=None)
            run(["repo", "sync", "-c", "--no-clone-bundle", "--no-tags"],
                cwd=self.source, stdout=None)
        print(f"Updated SOURCE to CONTROL {commit}; run prepare next")

    def prepare(self):
        with workspace_lock(self.source):
            if (self.source / PREPARED).exists():
                raise RebuildError("Preparation record already exists; inspect rather than reapply")
            inputs = self.input_hashes()
            groups = {}
            for entry, path in self.patches():
                groups.setdefault(entry["repo"], bytearray()).extend(path.read_bytes() + b"\n")
            # Check every project before changing any project. No reset/clean/reverse fallback.
            for name, diff in groups.items():
                repo = child(self.source, name)
                self.clean(repo)
                if git(repo, "rev-parse", "HEAD").decode().strip() != self.baseline["repo_heads"][name]:
                    raise RebuildError(f"Unexpected source HEAD: {name}")
                git(repo, "apply", "--check", "-", input=bytes(diff))
            for name, diff in groups.items():
                git(child(self.source, name), "apply", "-", input=bytes(diff))
            record = {"inputs": inputs, "repositories": {
                name: self.snapshot(child(self.source, name)) for name in groups}}
            write_json(self.source / PREPARED, record)
        print(f"Prepared patches; recorded {self.source / PREPARED}")

    def check_prepared(self):
        record = read_json(self.source / PREPARED)
        if record["inputs"] != self.input_hashes():
            raise RebuildError("Prepared inputs changed; inspect before rebuilding")
        expected_repos = {entry["repo"] for entry in self.series["patches"]}
        if set(record["repositories"]) != expected_repos:
            raise RebuildError("Preparation record has the wrong project set")
        for name, previous in record["repositories"].items():
            if self.snapshot(child(self.source, name)) != previous:
                raise RebuildError(f"Prepared worktree changed: {name}")
        return record

    def check_source(self):
        xml = run(["repo", "manifest", "-r"], cwd=self.source)
        actual = projects(xml)
        revisions = lambda mapping: {path: item["revision"] for path, item in mapping.items()}
        if revisions(actual) != revisions(self.locked):
            raise RebuildError("Actual repo manifest path/revision mapping differs from the lock")
        patched = {entry["repo"] for entry in self.series["patches"]}
        for name in self.locked:
            if name not in patched:
                self.clean(child(self.source, name))
        return xml

    def build(self):
        with workspace_lock(self.source):
            self.clean(self.control)
            manifest = self.check_source()
            prepared = self.check_prepared()
            marker = self.out / OUT_KERNEL
            if marker.exists() and marker.read_text().strip() != self.kernel:
                raise RebuildError(f"OUT belongs to kernel variant {marker.read_text().strip()}: {self.out}")
            keys = self.source / "vendor/evolution-priv/keys"
            for name in ("testkey.x509.pem", "testkey.pk8"):
                path = keys / name
                if inside(path.resolve(), self.control) or not path.is_file() or not path.stat().st_size:
                    raise RebuildError(f"Prepare existing external signing material first: {path}")
            release = read_json(self.control / "certificates/release-info.json")
            commit = git(self.control, "rev-parse", "HEAD").decode().strip()
            self.artifacts.mkdir(parents=True, exist_ok=True)
            prefix = "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-"
            directory = Path(tempfile.mkdtemp(prefix=prefix, dir=self.artifacts))
            print(f"Build log and result: {directory}", flush=True)
            (directory / "manifest.xml").write_bytes(manifest)
            write_json(directory / "prepared-inputs.json", prepared)
            result = {"status": "FAILED", "control_commit": commit, "signing": self.signing,
                      "kernel": self.kernel,
                      "out": str(self.out), "build_exit_code": None, "exit_code": 1,
                      "validation": "Not performed: APK keyset, native signatures, first boot and OTA"}
            try:
                env = environment()
                variant = self.profile["kernel_variants"][self.kernel]
                env.update(self.profile["environment"], **variant["environment"])
                out_dir = os.path.relpath(self.out, self.source)
                env.update(OUT_DIR=out_dir, EVO_KEEP_TARGET_FILES="true")
                self.out.mkdir(parents=True, exist_ok=True)
                marker.write_text(self.kernel + "\n")
                with (directory / "build.log").open("xb") as log:
                    try:
                        run(["bash", "--noprofile", "--norc", "-c", BUILD_SHELL, "martini-build",
                             self.profile["lunch"], out_dir, directory, keys,
                             release["certificate_der_sha256"] if self.signing == "release" else "",
                             variant["target"]],
                            cwd=self.source, stdout=log, env=env)
                    except subprocess.CalledProcessError as exc:
                        result["build_exit_code"] = exc.returncode
                        raise
                result["build_exit_code"] = 0
                version = (directory / "lineage-version.txt").read_text().strip()
                product = self.out / "target/product/martini"
                if variant["target"] == "bootimage":
                    # A kernel-only variant: its boot.img pairs with the same-commit normal ROM.
                    boot = product / "boot.img"
                    if not boot.is_file() or not boot.stat().st_size:
                        raise RebuildError(f"boot.img is missing: {boot}")
                    archived = directory / f"{version}-{self.kernel}-boot.img"
                    shutil.copyfile(boot, archived)
                    result["artifacts"] = {archived.name: fingerprint(archived)}
                else:
                    self.archive_rom(product, version, directory, result)
                result["ota_certificate_der_sha256"] = fingerprint(directory / "ota-certificate.der")["sha256"]
                result.update(status="BUILT_AND_ARCHIVED_UNVALIDATED", exit_code=0)
            except subprocess.CalledProcessError as exc:
                result["exit_code"] = exc.returncode
                raise
            finally:
                write_json(directory / "result.json", result)
            print(f"BUILT_AND_ARCHIVED_UNVALIDATED: {directory}")

    def archive_rom(self, product, version, directory, result):
        package = product / (version + ".zip")
        target_files = product / "obj/PACKAGING/target_files_intermediates/lineage_martini-target_files"
        if not package.is_file() or not package.stat().st_size:
            raise RebuildError(f"Actual LINEAGE_VERSION ZIP is missing: {package}")
        for name in ("META", "IMAGES"):
            if not (target_files / name).is_dir() or not any((target_files / name).iterdir()):
                raise RebuildError(f"Original target-files {name} is missing: {target_files}")
        shutil.copyfile(package, directory / package.name)
        archive = directory / "target-files.tar.zst"
        run(["tar", "--zstd", "-cf", archive, "-C", target_files, "."])
        result["artifacts"] = {path.name: fingerprint(path)
                               for path in (directory / package.name, archive)}

    def dry_run(self, command):
        print(f"DRY RUN {command}: CONTROL={self.control} SOURCE={self.source}")
        if command == "init":
            print("Require a clean committed CONTROL and nonexistent/empty SOURCE.")
            if self.restore:
                project = self.locked[self.restore["repo"]]
                print(f"Verify --source-bundle; mirror {project['name']}.git at {project['revision']}.")
            print(f"repo init -u {self.control} -b CONTROL_COMMIT -m {self.profile['manifest']} --git-lfs")
            print("repo sync -c --no-clone-bundle --no-tags")
        elif command == "update":
            print("Require clean committed CONTROL; verify SOURCE still equals its preparation record.")
            print("Undo only recorded changes, archive the record, then repo init -b CONTROL_COMMIT and repo sync.")
        elif command == "prepare":
            print("Verify internal patches and explicit --settings-patch; check every base/clean tree/apply first.")
            print(f"Apply grouped diffs with git apply; record HEAD/diff/untracked/input hashes in {PREPARED}.")
        else:
            print("Check repo manifest -r against lock, prepared hashes and clean unpatched projects.")
            variant = self.profile["kernel_variants"][self.kernel]
            print(f"Kernel {self.kernel} {variant['environment']}; OUT_DIR={self.out} EVO_KEEP_TARGET_FILES=true")
            print("Refuse an OUT already used by another kernel variant; source build/envsetup.sh")
            print(f"lunch {self.profile['lunch']}; check DEFAULT_SYSTEM_DEV_CERTIFICATE; m {variant['target']}")
            print(f"Use existing {self.source}/vendor/evolution-priv/keys, signing={self.signing}.")
            print(f"Archive the ZIP and original target-files (bootimage: boot.img) under {self.artifacts}/run-*.")
            print("Success means only BUILT_AND_ARCHIVED_UNVALIDATED, not native/device/OTA verification.")


BUILD_SHELL = r'''
set -e
source build/envsetup.sh || exit $?
lunch "$1" || exit $?
set -e
export OUT_DIR="$2" EVO_KEEP_TARGET_FILES=true
run_dir="$3"
keys="$4"
certificate=$(get_build_var DEFAULT_SYSTEM_DEV_CERTIFICATE)
case "$certificate" in
    vendor/evolution-priv/keys/testkey|"$keys/testkey") ;;
    vendor/evolution-priv/keys/releasekey|"$keys/releasekey")
        if ! [[ "$keys/releasekey.x509.pem" -ef "$keys/testkey.x509.pem" &&
                "$keys/releasekey.pk8" -ef "$keys/testkey.pk8" ]]; then
            printf '%s\n' 'releasekey must alias testkey in the official keys directory' >&2
            exit 2
        fi ;;
    *) printf '%s\n' 'DEFAULT_SYSTEM_DEV_CERTIFICATE is outside the official testkey/releasekey binding' >&2; exit 2 ;;
esac
openssl x509 -in "$certificate.x509.pem" -outform DER > "$run_dir/ota-certificate.der"
actual=$(sha256sum "$run_dir/ota-certificate.der")
if [[ -n "$5" && "${actual%% *}" != "$5" ]]; then
    printf '%s\n' 'Release OTA certificate DER fingerprint mismatch' >&2
    exit 2
fi
printf 'OTA public certificate SHA256: %s\n' "${actual%% *}"
version=$(get_build_var LINEAGE_VERSION)
case "$version" in
    ''|*[!a-zA-Z0-9._-]*) printf '%s\n' 'Unsafe or empty LINEAGE_VERSION' >&2; exit 2 ;;
esac
printf '%s\n' "$version" > "$run_dir/lineage-version.txt"
printf 'TARGET_KERNEL_SOURCE: %s\n' "$(get_build_var TARGET_KERNEL_SOURCE)"
m "$6"
'''


def main(argv=None, *, control=CONTROL):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "update", "prepare", "build"))
    parser.add_argument("--source", required=True, type=Path, metavar="ABS")
    parser.add_argument("--source-bundle", type=Path, metavar="FILE")
    parser.add_argument("--settings-patch", type=Path, metavar="FILE",
                        help="explicit external Settings diff; required by prepare and build")
    parser.add_argument("--out", type=Path, metavar="ABS", help="default: SOURCE/out")
    parser.add_argument("--artifacts", type=Path, metavar="ABS", help="default: SOURCE/artifacts")
    parser.add_argument("--signing", choices=("release", "self-build"), default="self-build")
    parser.add_argument("--kernel", default="normal", help="profile kernel variant: normal or ksu")
    parser.add_argument("--dry-run", action="store_true", help="read configuration and print steps only")
    args = parser.parse_args(argv)
    try:
        work = Rebuild(control, args.source, source_bundle=args.source_bundle,
                       settings_patch=args.settings_patch, out=args.out,
                       artifacts=args.artifacts, signing=args.signing, kernel=args.kernel)
        if args.dry_run:
            work.dry_run(args.command)
        else:
            getattr(work, args.command)()
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"Command failed (exit {exc.returncode}): {exc.cmd}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr.decode(errors="replace").strip(), file=sys.stderr)
        return exc.returncode if exc.returncode > 0 else 128 - exc.returncode
    except (RebuildError, OSError, ValueError, KeyError, ET.ParseError) as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
