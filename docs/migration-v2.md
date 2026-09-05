# Migrate to v2

Update callers deliberately. The v1 tag stays frozen; changing a caller to `@v2` opts that
repository into the contracts below. Test each release pipeline against the v2 branch or commit
before switching its production caller.

## Python: build shared, publish local

Replace calls to `python-publish.yml` with `python-build.yml`. The shared job builds distributions
and returns an `artifact-name` output. A normal job in the caller downloads that artifact and runs
`pypa/gh-action-pypi-publish` with `id-token: write`.

Use the [complete Python publishing example](../README.md#python-publishing). Keep build
dependencies and project code out of the publish job. Configure PyPI's trusted publisher with the
consuming repository and the filename of that local workflow. If PyPI specifies an environment, the
publish job must declare that same environment.

The previous instruction to register `shared-workflows/python-publish.yml` was incorrect. PyPI
[does not support that reusable-workflow identity](https://docs.pypi.org/trusted-publishers/troubleshooting/#reusable-workflows-on-github).
The v2 split fixes the identity mismatch without adding a long-lived API token.

## Concurrency belongs to the caller

All reusable workflows stop declaring top-level concurrency groups. Independent jobs in a release
pipeline no longer compete for a shared `release` group, and matrix calls do not cancel one another.

Keep CI cancellation in the top-level caller:

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Use a caller-level `pages` group for workflows deploying the same site. Release tags can run
independently. A workflow that changes a shared version branch may need its own group naming that
resource. GitHub's default queue retains only one pending run per group; use `queue: max` when
pending operations must be preserved. Publishing workflows use narrow job-level locks with
`queue: max` for mutable latest updates. Builds and notes still run in parallel.

## Grant permissions explicitly

Use the [permission table](../README.md#workflow-catalog) when updating callers. A reusable workflow
cannot elevate the caller's token. Rust CI requires `pull-requests: read` for change detection; OIDC
publishers require `id-token: write`; Pages requires `pages: write` and `id-token: write`.

Job-level permission blocks replace inherited blocks. Restate `contents: read` or `contents: write`
when the job needs repository access. Pass named secrets only to workflows that use them. Existing
`secrets: inherit` callers remain supported where GitHub permits inheritance.

## Rust profiles and release recovery

Move `--release` or `--profile` out of `cargo-build-args` and select `cargo-profile` instead
(default `release`). The default extra arguments are now `--locked`. Target and output-directory
overrides are rejected so compilation and artifact extraction use the same location.

For a failed downstream dispatch after version publication, pass `resume-release: true` with the
existing explicit `version`. The tag must be reachable from the dispatch branch. Resume can
regenerate release notes and retry dispatch without a second version bump or changelog edit.

Workspace selections accept Cargo package names or workspace-relative paths. Unknown entries fail.
Extra version files must exist, JSON version fields must be strings, and Markdown version edits are
limited to frontmatter.

## Release assets and metadata

Rust binary artifacts now contain `binaries-<target>.tar.gz`; extract that archive before executing
a downloaded binary. Archives retain executable permissions that raw Actions uploads lose.

GitHub Release passes matching binary archives through unchanged and packages other selected Actions
artifacts as `<artifact>.tar.gz` assets. Update scripts that previously expected flattened raw
binaries. Keeping artifact boundaries preserves platform names and avoids overwriting equal
filenames from different targets. The default `artifact-pattern` is now `binaries-*`; set a
different pattern to attach additional package artifacts.

The release workflow accepts an explicit `tag` when the caller ref is not the intended release tag.
Release tags must use `v?X.Y.Z` with optional SemVer prerelease and build metadata. Prereleases are
marked as such; an older stable release must not replace the newest stable release as latest.

Homebrew generates platform stanzas only for available Linux amd64 and macOS arm64 artifacts. Supply
at least one supported artifact, containing only its matching `binaries-<target>.tar.gz` archive.
Homebrew refuses to downgrade an existing formula to an older version. Published archives are
immutable: reruns reuse identical bytes and reject different content for the same version. The
optional `license` input defaults to `Apache-2.0`; set it to your project's SPDX license expression
when needed.

Docker accepts explicit tags through `version`. Only the newest stable SemVer release receives the
`latest` tag; prereleases and non-SemVer tags keep their explicit tag. Update consumers that relied
on a prerelease or an older release moving `latest`.

## Tool versions and promotion

The default Bun version becomes 1.4.1. Override `bun-version` if your workspace needs its previous
version while you validate the upgrade. Node 24 and Python 3.13 remain compatibility defaults. The
`pnpm-version` default becomes empty in Docs and moon CI. The project's `packageManager` or
`devEngines` pin selects pnpm; only unpinned projects fall back to version 10. Explicit overrides
must agree with the project pin. A pnpm 11 migration still needs consumer configuration review.

The uv setup action moves to the exact `v10.0.1` release. Its automatic caching disables cache use
for sensitive events, including `release` and `workflow_run`. Publishing jobs should not rely on a
warm cache for correctness.

Repository tag promotion now advances v2 only after CI succeeds for the exact main-branch commit.
The promotion workflow no longer picks the highest numbered major or moves a tag before validation.
Existing v1 callers keep their current implementation until their workflow references change.

The CI promotion gate includes formatting and lint checks, Python behavior fixtures, a Bun consumer
smoke test, and a Python build/download/install smoke test. The Python smoke installs and executes
the wheel without checking out source code in the consuming job.
