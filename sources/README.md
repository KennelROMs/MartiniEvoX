# External SettingsGoogle inputs

## Scope

The public control repository records identities, not the SettingsGoogle bundle,
original patch or complete source fixture. [`settings-google.json`](settings-google.json)
marks **independent public recovery as BLOCKED**: redistribution rights and an
authorized public recovery location have not been established.

An authorized existing holder may supply both external files for local source
preparation. That is distinct from public availability and does not grant
redistribution permission. No full ROM rebuild was performed for this
control-repository change.

## Fixed identities

| External input ID | Type | Bytes |
| --- | --- | ---: |
| `settings_google_bundle` | Git bundle | 1648368 |
| `settings_google_patch` | Original `git diff` patch | 1357 |

- Bundle SHA256: `57eafcf7b3a9b4823bf2b0404ab2673b9c9438e1d0bebb8f51531c36e8c67179`
- Original patch SHA256: `039b2f1591745b6168eef871cef9aebd135b0a48981979e4ece0206cdf109359`
- Project: `vendor/google/apps/SettingsGoogle`
- Required base: `86a6033a534f7e8039e3af6b7e53c9e244621512`
- Base bundle ref: `refs/heads/evox/cnb-martini-bringup`
- Corrected collector reference: `f38977d0fcfd117e76d5f18e4bbd453884122a4e`

The corrected reference is not the reconstruction base. The SettingsGoogle diff
is the third entry in [`patches/series.json`](../patches/series.json), using
`external_input: settings_google_patch` with no internal patch fallback. The other
five entries retain their original internal diff bytes. All six use `git apply`,
not `git am`, against the pinned base HEADs.

The descriptor's `--source-bundle` and `--settings-patch` names identify explicit
inputs for the recovery interface; they are **not unittest options**. Historical
path strings are provenance only, never default lookup paths. The upstream URL
is not a bundle download location or a guarantee that the rewritten base remains
fetchable. Source restoration belongs in the production recovery workflow, not
in a second implementation inside the test suite.

## Public offline contracts

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_baseline_inputs.py -v
```

These standard-library tests check locked manifest records, baseline/profile
rules, the five internal patch hashes, and external input identities and status.
They do not read historical evidence or original SettingsGoogle materials, run
Git subprocesses, import bundles, apply the external patch, restore sources or
build Android. Public synthetic tests elsewhere demonstrate control behavior,
not original third-party source equivalence.

## Previously completed offline verification

On 2026-10-01, in a maintainer's temporary workspace:

- The preserved bundle's size and SHA256 matched. Bundle verification, local
  import and `git fsck --full --strict` returned exit 0.
- Both specified commit objects were present in the complete history: 42 commits,
  1419 trees and 1498 blobs. The baseline has 487 files; the corrected tree has 491.
- The original patch's 1357 bytes and SHA256 matched the frozen candidate diff.
  Applying it to the baseline collector produced bytes identical to the corrected
  reference object and the candidate's recorded source SHA256.
- No Git LFS pointer blobs were found. Bounded private-key/token/credential
  patterns had no matches across the 2959 objects. This is not a guarantee that
  no secrets exist.

These are recorded observations, not a current public source-validation command,
a license grant, an upstream availability check, or proof of a complete ROM rebuild.

## Redistribution review

No `LICENSE`, `LICENCE`, `NOTICE`, `COPYING`, `AUTHORS` or `COPYRIGHT` file was
found across the reviewed commit trees. Twenty-nine historical blobs contain
file-specific Apache headers, but these do not cover the entire bundle.

`Android.bp`, blob `dba728e98a92256b3a216372e4941b91e60b09f3`, has no
`default_applicable_licenses`. The collector's baseline blob
`7babcdca201d562dda986ccbca355e1086d0b2be` and corrected blob
`9ba996fbca0d651e6fba39bc1b164fc9a8f130df` have no file-level license notice.
No package-wide license evidence was established for them.

The history records stock icon and overlay imports. It also includes the
102691-byte `res/raw/fingerprint_location_animation.mp4`, blob
`076aa0fb9fcdb85edf573910b389b5e93c39c380`, introduced by
`0854ddecd618f8381ad702fac09ddff58b17f71f`. Redistribution permission for that
asset was not established; it is the one non-UTF-8 blob observed.

Excluded historical materials include:

- `tests/fixtures/settings_google_screen_collector.before.json`
- `patches/vendor_google_apps_SettingsGoogle/0001-fix-screen-collector.patch`

The original fixture, patch context, bundle and historical source copies are not
relicensed by the control repository's Apache-2.0 license. No recovery payload or
invented third-party license/author notice has been added here.

Changing the public recovery gate requires verifiable rights, required notices,
an authorized retrieval route, fixed artifact identities and renewed verification.
A replacement recovery input must not silently change the preserved baseline.
