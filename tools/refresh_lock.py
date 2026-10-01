#!/usr/bin/env python3
# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
"""Pin the current Evolution-X manifest plus manifests/martini.xml into a new lock.

Repo merges the manifests; every project revision is resolved with git ls-remote.
Writes manifests/locked/martini-ID.xml and baselines/ID.json, points the profile and
patch series at them, and keeps the KernelSU Next version pins in step. Whether the
patches still apply is checked afterwards by rebuild.py prepare on real source.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


CONTROL = Path(__file__).resolve().parents[1]
EVO_MANIFEST = "https://github.com/Evolution-X/manifest"
SHA = re.compile(r"^[0-9a-f]{40}$")
# Evolution-X rewrites cnb; a shallow SHA fetch keeps pinned commits syncable.
SHALLOW_REMOTES = {"evo"}
# The Evolution-X manifest uses a relative GitHub remote; locks are portable.
REMOTE_FETCH = {"..": "https://github.com"}
KSU_REPO = "external/KernelSU-Next"
KSU_PATCH = "patches/ksu/0001-martini-ksu-kernel-variant.patch"
KSU_PINS = re.compile(r"KSU_VERSION_OVERRIDE=\d+ KSU_VERSION_TAG_OVERRIDE=\S+")


class RefreshError(Exception):
    pass


def run(command, cwd=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True,
                          text=True, timeout=600).stdout


def parse_ls_remote(output, expr):
    refs = {}
    for line in output.splitlines():
        sha, ref = line.split("\t")
        refs[ref] = sha
    candidates = [expr] if expr.startswith("refs/") else ["refs/heads/" + expr, "refs/tags/" + expr]
    for ref in candidates:
        # An annotated tag resolves to the commit it points at.
        for name in (ref + "^{}", ref):
            if name in refs:
                return refs[name]
    raise RefreshError(f"Cannot resolve {expr}")


def ls_remote(url, expr):
    if SHA.match(expr):
        return expr
    try:
        return parse_ls_remote(run(["git", "ls-remote", url]), expr)
    except (RefreshError, subprocess.SubprocessError) as exc:
        raise RefreshError(f"{url} {expr}: {exc}") from exc


def pin(root, resolve):
    remotes = {r.get("name"): r for r in root.findall("remote")}
    default = root.find("default")
    projects = root.findall("project")
    used = {p.get("remote", default.get("remote")) for p in projects}
    for name, remote in list(remotes.items()):
        if name not in used and name != default.get("remote"):
            root.remove(remote)
        elif remote.get("fetch") in REMOTE_FETCH:
            remote.set("fetch", REMOTE_FETCH[remote.get("fetch")])
    jobs = []
    for project in projects:
        remote = remotes[project.get("remote", default.get("remote"))]
        expr = project.get("revision") or remote.get("revision") or default.get("revision")
        jobs.append((project, remote.get("fetch").rstrip("/") + "/" + project.get("name"), expr))
    with ThreadPoolExecutor(16) as pool:
        shas = list(pool.map(lambda job: resolve(job[1], job[2]), jobs))
    for (project, _, expr), sha in zip(jobs, shas):
        project.set("revision", sha)
        if not SHA.match(expr):
            project.set("upstream", project.get("upstream", expr))
            project.set("dest-branch", project.get("dest-branch", expr))
        if (project.get("remote", default.get("remote")) in SHALLOW_REMOTES
                and project.get("clone-depth") is None):
            project.set("clone-depth", "1")
    return root


def ksu_version(url, sha, workdir):
    # Same numbers KernelSU Next's Kbuild derives from a full clone with tags.
    git_dir = Path(workdir) / "ksu.git"
    run(["git", "clone", "--quiet", "--bare", "--filter=blob:none", url, str(git_dir)])
    count = int(run(["git", "-C", str(git_dir), "rev-list", "--count", sha]).strip())
    tag = run(["git", "-C", str(git_dir), "describe", "--tags", "--abbrev=0", sha]).strip()
    return 30000 + count + 289, tag


def fingerprint(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def refresh(control, lock_id, branch):
    lock_rel = f"manifests/locked/martini-{lock_id}.xml"
    baseline_rel = f"baselines/{lock_id}.json"
    for rel in (lock_rel, baseline_rel):
        if (control / rel).exists():
            raise RefreshError(f"Refusing to overwrite {rel}")
    profile_path = control / "profiles/martini.json"
    profile = json.loads(profile_path.read_text())
    previous = json.loads((control / profile["baseline"]).read_text())
    series_path = control / profile["patch_series"]
    series = json.loads(series_path.read_text())
    with tempfile.TemporaryDirectory() as work:
        run(["repo", "init", "--quiet", "-u", EVO_MANIFEST, "-b", branch], cwd=work)
        local = Path(work) / ".repo/local_manifests"
        local.mkdir()
        shutil.copyfile(control / "manifests/martini.xml", local / "martini.xml")
        run(["repo", "manifest", "-o", "merged.xml"], cwd=work)
        manifest_commit = run(["git", "-C", str(Path(work) / ".repo/manifests"), "rev-parse", "HEAD"]).strip()
        root = pin(ET.parse(Path(work) / "merged.xml").getroot(), ls_remote)
        projects = {p.get("path", p.get("name")): p for p in root.findall("project")}
        ksu = projects[KSU_REPO]
        remotes = {r.get("name"): r.get("fetch") for r in root.findall("remote")}
        version, tag = ksu_version(remotes[ksu.get("remote")].rstrip("/") + "/" + ksu.get("name"),
                                   ksu.get("revision"), work)
    ET.indent(root, "  ")
    (control / lock_rel).write_bytes(ET.tostring(root, encoding="UTF-8", xml_declaration=True) + b"\n")

    patch = control / KSU_PATCH
    text = patch.read_text()
    if len(KSU_PINS.findall(text)) != 1:
        raise RefreshError(f"Expected one KSU version pin line in {KSU_PATCH}")
    patch.write_text(KSU_PINS.sub(f"KSU_VERSION_OVERRIDE={version} KSU_VERSION_TAG_OVERRIDE={tag}", text))

    heads = {}
    for entry in series["patches"]:
        heads[entry["repo"]] = entry["base_revision"] = projects[entry["repo"]].get("revision")
        if entry.get("patch"):
            entry["sha256"] = fingerprint(control / entry["patch"])["sha256"]
    heads["kernel/oneplus/sm8350"] = projects["kernel/oneplus/sm8350"].get("revision")
    kernel = previous["kernel"]
    for variant in kernel["variants"].values():
        variant["base_revision"] = heads["kernel/oneplus/sm8350"]
    kernel["variants"]["ksu"]["kernelsu_next"].update(revision=ksu.get("revision"), version=version,
                                                      version_tag=tag)
    baseline = {
        "schema_version": 1,
        "id": lock_id,
        "device": "martini",
        "source": {
            "evolution_manifest": EVO_MANIFEST, "branch": branch, "commit": manifest_commit,
            "local_manifest": {"path": "manifests/martini.xml",
                               "sha256": fingerprint(control / "manifests/martini.xml")["sha256"]},
            "resolved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "manifest": {"portable": {"path": lock_rel, **fingerprint(control / lock_rel)},
                     "project_count": len(projects)},
        "repo_heads": heads,
        "kernel": kernel,
        "pixelos_ledger": previous.get("pixelos_ledger", "docs/PIXELOS.md"),
        "candidate_rom": None,
        "signing": previous["signing"],
    }
    (control / baseline_rel).write_text(json.dumps(baseline, indent=2) + "\n")
    series["baseline"] = baseline_rel
    series_path.write_text(json.dumps(series, indent=2) + "\n")
    profile.update(id=f"martini-{lock_id}", baseline=baseline_rel, manifest=lock_rel)
    profile_path.write_text(json.dumps(profile, indent=2) + "\n")
    return baseline


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="new lock id, e.g. 20261002")
    parser.add_argument("--branch", default="cnb", help="Evolution-X manifest branch")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9A-Za-z.-]+", args.id):
        print("Refused: unsafe --id", file=sys.stderr)
        return 1
    try:
        baseline = refresh(CONTROL, args.id, args.branch)
    except (RefreshError, subprocess.SubprocessError, OSError, KeyError) as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1
    print(f"Pinned {baseline['manifest']['project_count']} projects from Evolution-X manifest "
          f"{baseline['source']['commit']} into {baseline['manifest']['portable']['path']}")
    for repo, sha in sorted(baseline["repo_heads"].items()):
        print(f"  {repo}: {sha}")
    ksu = baseline["kernel"]["variants"]["ksu"]["kernelsu_next"]
    print(f"  KernelSU Next {ksu['revision']} version {ksu['version']} {ksu['version_tag']}")
    print("Next: commit, then rebuild.py update and prepare to confirm the patches still apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
