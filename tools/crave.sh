#!/bin/bash
# Copyright 2026 MartiniEvoX contributors
# SPDX-License-Identifier: Apache-2.0
#
# Runs on the crave build node from the workspace root (the Android SOURCE):
#   sync CONTROL_REF             adopt a foreign snapshot once, then update/prepare SOURCE
#   build CONTROL_REF            sync, then build the ROM and its paired KSU boot.img;
#                                upload too when SF_USER/SF_PROJECT are set
#   upload ROM_RUN KSU_RUN       rsync both to SourceForge and print the Updater entry
# No flashing, clean, reset or force-sync; a failed build keeps its log in the run directory.
# --crave: crave hooks compilers (X becomes its hook, the original is mbt-bin-X); unpatched
# projects may carry them, and update puts the originals back only where sync moves a project.
set -euo pipefail

source_dir=$PWD
control=${MARTINI_CONTROL:-$HOME/MartiniEvoX}
secrets=$source_dir/.martini-secrets

need() {
    local tool
    for tool in "$@"; do
        command -v "$tool" > /dev/null || { echo "Missing tool on build node: $tool" >&2; exit 2; }
    done
}

# CONTROL lives outside SOURCE; the node's home may not persist, so clone when absent.
checkout_control() {
    if [[ ! -d $control/.git ]]; then
        git clone --quiet https://github.com/KennelROMs/MartiniEvoX.git "$control"
    fi
    git -C "$control" fetch --quiet origin
    # Repo only finds the manifest revision on a branch of CONTROL, not a detached HEAD.
    git -C "$control" checkout --quiet -B martini-build "$1"
    echo "CONTROL $(git -C "$control" rev-parse HEAD)"
}

built() {
    python3 "$control/tools/rebuild.py" build --source "$source_dir" --crave --signing release "$@" |
        tee /dev/stderr | sed -n 's/^BUILT_AND_ARCHIVED_UNVALIDATED: //p'
}

sync() {
    local ref=${1:?usage: crave.sh sync CONTROL_REF}
    need git repo python3
    checkout_control "$ref"
    if [[ ! -e $source_dir/.martini-prepared.json && ! -d $source_dir/.martini-history ]]; then
        python3 "$control/tools/rebuild.py" adopt --source "$source_dir" --crave
    fi
    python3 "$control/tools/rebuild.py" update --source "$source_dir" --crave --clone-depth 1
    python3 "$control/tools/rebuild.py" prepare --source "$source_dir"
}

build() {
    local ref=${1:?usage: crave.sh build CONTROL_REF} rom ksu
    need git repo python3 openssl zstd tar
    [[ -z ${SF_USER:-}${SF_PROJECT:-} ]] || need rsync ssh
    sync "$ref"
    rom=$(built --out "$source_dir/out")
    ksu=$(built --kernel ksu --out "$source_dir/out-ksu")
    echo "ROM run: $rom"
    echo "KSU run: $ksu"
    if [[ -n ${SF_USER:-} && -n ${SF_PROJECT:-} ]]; then
        upload "$rom" "$ksu"
    fi
}

upload() {
    local rom=${1:?usage: crave.sh upload ROM_RUN_DIR KSU_RUN_DIR} ksu=${2:?KSU_RUN_DIR} zip boot commit
    : "${SF_USER:?set SF_USER}" "${SF_PROJECT:?set SF_PROJECT}"
    need git python3 rsync ssh
    zip=$(echo "$rom"/EvolutionX-*.zip)
    boot=$(echo "$ksu"/*-ksu-boot.img)
    [[ -f $zip && -f $boot ]] || { echo "Expected one ROM ZIP and one KSU boot.img" >&2; exit 2; }
    # Publish only a pair built from the same CONTROL commit.
    commit=$(python3 - "$rom/result.json" "$ksu/result.json" <<'EOF'
import json, sys
rom, ksu = (json.load(open(path)) for path in sys.argv[1:])
if {rom["status"], ksu["status"]} != {"BUILT_AND_ARCHIVED_UNVALIDATED"}:
    sys.exit("Both runs must be BUILT_AND_ARCHIVED_UNVALIDATED")
if rom["control_commit"] != ksu["control_commit"] or (rom["kernel"], ksu["kernel"]) != ("normal", "ksu"):
    sys.exit("ROM and KSU runs do not pair (kernel variant or CONTROL commit differs)")
print(rom["control_commit"])
EOF
)
    checkout_control "$commit"
    rsync -avP -e "ssh -i $secrets/sourceforge -o IdentitiesOnly=yes \
-o UserKnownHostsFile=$secrets/known_hosts -o StrictHostKeyChecking=accept-new" \
        "$zip" "$boot" "$SF_USER@frs.sourceforge.net:/home/frs/project/$SF_PROJECT/martini/"
    python3 "$control/tools/ota_json.py" "$zip" \
        --url "https://sourceforge.net/projects/$SF_PROJECT/files/martini/${zip##*/}/download" \
        --maintainer "${MAINTAINER:-}" | tee "$rom/martini.json"
}

case "${1:-}" in
    sync|build|upload) "$@" ;;
    *) echo "usage: crave.sh sync|build CONTROL_REF | upload ROM_RUN_DIR KSU_RUN_DIR" >&2; exit 2 ;;
esac
