<h1 align="center">⚡ shared-workflows</h1>

<p align="center">
  <strong>Reusable CI and releases for the hyperb1iss ecosystem</strong><br>
  <sub>13 reusable workflows · Rust, Python, Bun, docs, and containers</sub>
</p>

<p align="center">
  <a href="https://github.com/hyperb1iss/shared-workflows/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/hyperb1iss/shared-workflows/ci.yml?branch=main&style=for-the-badge&logo=github&logoColor=white&label=CI&color=e135ff" alt="CI status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-80ffea?style=for-the-badge" alt="Apache 2.0 license"></a>
</p>

Centralize the setup, keep the project decisions local. Call a shared workflow from your repository,
pass its inputs, and keep service containers, release triggers, and workflow orchestration in your
caller.

**Moving from v1?** Read the [v2 migration guide](docs/migration-v2.md). Python publishing changes
shape, and callers now own workflow-level concurrency. The v1 tag stays frozen while v2 receives
validated updates.

## Start here

Create this file in your repository. The caller grants the permissions required by the shared jobs.

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read
  pull-requests: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v2
    with:
      workspace: true
```

Callers must live directly in `.github/workflows/`. Use `@v2` for compatible updates or a full
commit SHA for an immutable revision. Pass named secrets when needed; `secrets: inherit` is
available for eligible repositories but is unnecessary for jobs that do not consume secrets.

## Workflow catalog

| Workflow                                                     | Purpose                               | Caller permissions                                  |
| ------------------------------------------------------------ | ------------------------------------- | --------------------------------------------------- |
| [Rust CI](.github/workflows/rust-ci.yml)                     | Fmt, clippy, nextest, cargo-deny      | `contents: read`, `pull-requests: read`             |
| [Rust publish](.github/workflows/rust-publish.yml)           | Publish crates in dependency order    | `contents: read`, `id-token: write`                 |
| [Rust release](.github/workflows/rust-release.yml)           | Bump version, validate, tag, dispatch | `contents: write`, `actions: write`                 |
| [Rust artifacts](.github/workflows/rust-build-artifacts.yml) | Build binaries and Linux packages     | `contents: read`                                    |
| [Python CI](.github/workflows/python-ci.yml)                 | Ruff and pytest                       | `contents: read`                                    |
| [Python build](.github/workflows/python-build.yml)           | Build distribution artifacts          | `contents: read`                                    |
| [Bun CI](.github/workflows/bun-ci.yml)                       | Check and build a workspace           | `contents: read`                                    |
| [npm publish](.github/workflows/npm-publish.yml)             | Build and publish with OIDC           | `contents: read`, `id-token: write`                 |
| [Docs deploy](.github/workflows/docs-deploy.yml)             | VitePress or MkDocs to Pages          | `contents: read`, `pages: write`, `id-token: write` |
| [GitHub release](.github/workflows/github-release.yml)       | Release notes and attached assets     | `contents: write`, `actions: read`                  |
| [Homebrew update](.github/workflows/homebrew-update.yml)     | Package assets and update a tap       | `contents: write`                                   |
| [Docker publish](.github/workflows/docker-publish.yml)       | DockerHub, GHCR, or both              | `contents: read`, `packages: write`                 |
| [moon CI](.github/workflows/moon-ci.yml)                     | Polyglot workspace tasks              | `contents: read`                                    |

The repository also has CI and an internal version-tag promotion workflow. The promotion workflow is
called by repository CI after validation; consumers should use the public catalog above. GitHub
allows a called workflow to reduce permissions, but
[it cannot raise the caller's grant](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations).

## Python publishing

Build distributions in the shared workflow and publish from a normal job in your repository.
Register your repository and `publish.yml` with PyPI. If you configure a publishing environment in
PyPI, add the same environment to the `publish` job.

```yaml
# .github/workflows/publish.yml
name: Publish Python
on:
  push:
    tags: ['v*']

permissions:
  contents: read

jobs:
  build:
    uses: hyperb1iss/shared-workflows/.github/workflows/python-build.yml@v2

  publish:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v8
        with:
          name: ${{ needs.build.outputs.artifact-name }}
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

PyPI's
[trusted publishing limitation](https://docs.pypi.org/trusted-publishers/troubleshooting/#reusable-workflows-on-github)
requires the publish step to run in the caller. Build code runs separately from the job authorized
to publish. For a workspace, pass `package-names: 'my-core my-cli'` to the build job.

## Rust release pipeline

Publish and build independently, then create the GitHub release. Configure crates.io trusted
publishing for your package before the first run. Store `ANTHROPIC_API_KEY` in the caller repository
for generated release notes.

```yaml
# .github/workflows/cicd.yml
name: Release artifacts
on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  publish:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-publish.yml@v2
    permissions:
      contents: read
      id-token: write

  build:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-build-artifacts.yml@v2
    with:
      binaries: my-cli

  release:
    needs: [publish, build]
    uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v2
    permissions:
      contents: write
      actions: read
    with:
      attach-artifacts: true
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Dispatch this workflow against a version tag. To automate version changes, add a separate caller for
`rust-release.yml` with `contents: write` and `actions: write`, and set `cicd-workflow` to
`cicd.yml`. Branch protection may require its optional `release-token` secret. Keep this downstream
workflow dispatch-only: a personal token can also trigger tag-push workflows, causing duplicate
publication if both triggers are enabled. For manual-tag pipelines without the release orchestrator,
use a tag-push trigger instead.

## Pages deployment

Configure the repository's Pages source as GitHub Actions. This example expects a pnpm lockfile and
a build script in `docs/`.

```yaml
# .github/workflows/docs.yml
name: Docs
on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  docs:
    uses: hyperb1iss/shared-workflows/.github/workflows/docs-deploy.yml@v2
    with:
      engine: vitepress
      docs-dir: docs
```

For MkDocs, set `engine: mkdocs` and point `docs-dir` at the uv project containing your MkDocs
configuration. Keep its lockfile committed.

## Concurrency

Reusable workflows do not declare workflow-level concurrency groups. Independent publish, build, and
release jobs can run together without colliding on a repository-wide group name.

Use caller-level cancellation for CI and a caller-level Pages group when deployments share a site.
Release tags normally run independently. If a release process updates a shared branch or resource,
choose a group in its caller that names that resource. The default GitHub concurrency queue retains
only one pending run; choose `queue: max` when pending operations must be preserved.

The publishing workflows use narrow job-level groups with `queue: max` to protect mutable latest
updates. Builds and release-note generation remain parallel; only the final latest update shares a
lock with competing releases.

## Rust workflows

### rust-ci.yml

Checks formatting, clippy, tests, and dependency policy. Changes outside configured paths can skip
Rust jobs.

| Input               | Type    | Default    | Description                      |
| ------------------- | ------- | ---------- | -------------------------------- |
| `change-detection`  | boolean | `true`     | Enable dorny/paths-filter gating |
| `change-filters`    | string  | `''`       | Extra path filters (YAML)        |
| `system-deps`       | string  | `''`       | apt packages to install          |
| `workspace`         | boolean | `false`    | `--workspace` flag               |
| `all-features`      | boolean | `true`     | `--all-features` flag            |
| `all-targets`       | boolean | `true`     | `--all-targets` for clippy       |
| `nextest`           | boolean | `true`     | Use cargo-nextest                |
| `cargo-deny`        | boolean | `true`     | Run cargo-deny audit             |
| `nightly-fmt`       | boolean | `false`    | Nightly rustfmt                  |
| `extra-clippy-args` | string  | `''`       | Additional clippy arguments      |
| `rust-toolchain`    | string  | `'stable'` | Rust toolchain version           |

**Jobs:** `changes` gates independent `check`, `test`, and `deny` jobs.

### rust-publish.yml

Publishes to crates.io via OIDC trusted publishing. No tokens to manage.

| Input           | Type   | Default | Description                         |
| --------------- | ------ | ------- | ----------------------------------- |
| `crates`        | string | `''`    | Space-separated crates in order     |
| `publish-delay` | number | `30`    | Seconds between workspace publishes |
| `system-deps`   | string | `''`    | apt packages needed for build       |

### rust-release.yml

Version bump → tag → trigger CI/CD. Each consumer keeps a thin `release.yml` with
`workflow_dispatch` inputs that calls this shared workflow.

| Input                          | Type    | Default           | Description                                                |
| ------------------------------ | ------- | ----------------- | ---------------------------------------------------------- |
| `version`                      | string  | `''`              | Explicit version (overrides bump)                          |
| `bump`                         | string  | `'patch'`         | `patch` / `minor` / `major`                                |
| `resume-release`               | boolean | `false`           | Retry downstream dispatch for an existing explicit version |
| `dry_run`                      | boolean | `false`           | Build + test only                                          |
| `system-deps`                  | string  | `''`              | apt packages                                               |
| `workspace`                    | boolean | `false`           | Workspace mode                                             |
| `workspace-crates`             | string  | `''`              | Cargo package names or workspace-relative paths            |
| `all-features`                 | boolean | `true`            | `--all-features` for build/test                            |
| `nextest`                      | boolean | `true`            | Use nextest for validation                                 |
| `generate-release-notes`       | boolean | `false`           | Generate via git-iris                                      |
| `generate-changelog`           | boolean | `false`           | Update CHANGELOG.md                                        |
| `release-notes-model`          | string  | `'claude-opus-5'` | AI model for release notes and changelog                   |
| `release-notes-provider`       | string  | `'anthropic'`     | LLM provider for git-iris                                  |
| `cicd-workflow`                | string  | `'cicd.yml'`      | Downstream workflow to trigger                             |
| `pass-run-id`                  | boolean | `false`           | Pass release_run_id to downstream                          |
| `patch-workspace-dep-versions` | boolean | `false`           | Patch version pins for path deps in root Cargo.toml        |
| `version-files`                | string  | `''`              | Extra files to patch (JSON, YAML frontmatter)              |

The `resume-release` input requires an explicit existing version tag reachable from the dispatch
branch. Resume regenerates optional notes and retries dispatch without changing the version or
changelog. Invalid workspace entries and missing version files fail before publication. JSON version
fields must already exist as strings; Markdown version fields must be inside frontmatter.

### rust-build-artifacts.yml

Cross-platform binary builds with a 4-target matrix.

| Input              | Type    | Default                                             | Description                                       |
| ------------------ | ------- | --------------------------------------------------- | ------------------------------------------------- |
| `binaries`         | string  | **required**                                        | Binary names to extract                           |
| `system-deps`      | string  | `''`                                                | Linux apt packages                                |
| `targets`          | string  | `'linux-amd64 linux-arm64 macos-arm64 windows-gnu'` | Build targets                                     |
| `build-packages`   | boolean | `false`                                             | Build .deb + .rpm                                 |
| `cargo-profile`    | string  | `'release'`                                         | Cargo profile used for compilation and extraction |
| `cargo-build-args` | string  | `'--locked'`                                        | Extra build args                                  |

Select the output profile with `cargo-profile`. Extra arguments cannot override the profile, target,
or target directory. Each Actions artifact contains a `binaries-<target>.tar.gz` archive preserving
executable permissions. Extract the archive before running a downloaded binary.

**Matrix:**

| Target        | Runner             | Rust Target                 |
| ------------- | ------------------ | --------------------------- |
| `linux-amd64` | `ubuntu-latest`    | `x86_64-unknown-linux-gnu`  |
| `linux-arm64` | `ubuntu-24.04-arm` | `aarch64-unknown-linux-gnu` |
| `macos-arm64` | `macos-latest`     | `aarch64-apple-darwin`      |
| `windows-gnu` | `windows-latest`   | `x86_64-pc-windows-gnu`     |

---

## Python workflows

### python-ci.yml

Lint + test using the Astral stack (uv, ruff). Single job with lint and test steps.

| Input            | Type    | Default  | Description                |
| ---------------- | ------- | -------- | -------------------------- |
| `python-version` | string  | `'3.13'` | Python version             |
| `ruff`           | boolean | `true`   | Run ruff lint + format     |
| `pytest`         | boolean | `true`   | Run pytest                 |
| `pytest-args`    | string  | `''`     | Extra pytest arguments     |
| `system-deps`    | string  | `''`     | apt packages               |
| `rust-toolchain` | boolean | `false`  | Install Rust (native deps) |

**Jobs:** `ci` (ruff check + format → pytest)

For a version matrix, set `strategy.matrix` on the calling job and pass each version through
`python-version`. Projects requiring service containers should define a local job with their service
configuration.

### python-build.yml

Builds wheels and source distributions, then uploads a distribution artifact. Publishing runs in an
ordinary job in your repository; the complete example above uses PyPI trusted publishing.

| Input           | Type   | Default | Description                                                |
| --------------- | ------ | ------- | ---------------------------------------------------------- |
| `package-dir`   | string | `'.'`   | Directory containing pyproject.toml in single-package mode |
| `package-names` | string | `''`    | Space-separated workspace package names                    |
| `checkout-ref`  | string | `''`    | Git ref to build; empty uses the caller ref                |

Additional build inputs are `python-version` (default `3.13`) and `artifact-name` (default
`python-dists`). Give each matrix call a distinct artifact name.

The workflow output `artifact-name` identifies the uploaded distribution artifact. Download that
artifact into `dist/` in the caller's publish job. The publish job needs no checkout, dependency
installation, or build commands.

---

## Common workflows

### docs-deploy.yml

VitePress or MkDocs → GitHub Pages with OIDC deployment.

| Input            | Type   | Default       | Description                           |
| ---------------- | ------ | ------------- | ------------------------------------- |
| `docs-dir`       | string | `'docs'`      | Path to docs directory                |
| `node-version`   | string | `'24'`        | Node.js version                       |
| `pnpm-version`   | string | `''`          | Project pin, or pnpm 10 when unpinned |
| `engine`         | string | `'vitepress'` | `vitepress` or `mkdocs`               |
| `python-version` | string | `'3.13'`      | Python version (MkDocs only)          |

The `pnpm-version` input defaults to empty, selecting the project's `packageManager` or `devEngines`
pin. Unpinned projects fall back to pnpm 10. An explicit override must agree with the project pin.
The same resolution applies to moon CI.

### github-release.yml

Creates a GitHub Release with AI-generated notes from
[git-iris](https://github.com/hyperb1iss/git-iris).

| Input                    | Type    | Default           | Description                                     |
| ------------------------ | ------- | ----------------- | ----------------------------------------------- |
| `tag`                    | string  | `''`              | Explicit release tag; empty uses the caller ref |
| `release-notes-model`    | string  | `'claude-opus-5'` | AI model for release notes                      |
| `release-notes-provider` | string  | `'anthropic'`     | LLM provider                                    |
| `attach-artifacts`       | boolean | `false`           | Attach build artifacts                          |
| `artifact-pattern`       | string  | `'binaries-*'     | Glob for artifacts to attach                    |
| `release-notes-run-id`   | string  | `''`              | Use pre-generated notes from run                |
| `draft`                  | boolean | `false`           | Create as draft release                         |

The default artifact pattern selects binary builds. Set `artifact-pattern` explicitly to include
other artifacts. Binary archives pass through unchanged; other selected artifacts are packaged as
separate archive assets. The release retains target names and executable modes. Prerelease tags are
marked as prereleases; stable releases only become latest when their version is newest.

### homebrew-update.yml

Auto-updates the formula in [homebrew-tap](https://github.com/hyperb1iss/homebrew-tap) after a
release. Generates CamelCase Ruby class names automatically (e.g., `git-iris` → `GitIris`).

| Input          | Type   | Default                     | Description                  |
| -------------- | ------ | --------------------------- | ---------------------------- |
| `license`      | string | `'Apache-2.0'`              | SPDX license expression      |
| `formula-name` | string | **required**                | e.g., `git-iris` or `unifly` |
| `tap-repo`     | string | `'hyperb1iss/homebrew-tap'` | Target tap repository        |
| `description`  | string | **required**                | Formula description          |
| `homepage`     | string | **required**                | Formula homepage URL         |
| `binary-names` | string | **required**                | Space-separated binaries     |

**Artifact contract:** provide at least one supported Actions artifact named `binaries-linux-amd64`
or `binaries-macos-arm64`. Each must contain only its matching `binaries-<target>.tar.gz` archive,
with binaries at the archive root. Rust builds produce this format and preserve executable
permissions. Homebrew publishes platform archives and generates stanzas only for the platforms
present.

Optional top-level `share/` and `etc/` directories inside the payload install into Homebrew's
prefix. The formula installs each entry in `binary-names` and uses the supplied SPDX `license`.

The workflow updates only the formula through GitHub's Contents API and refuses to downgrade an
existing formula to an older version. Published archives are immutable: reruns reuse identical bytes
and reject different content for the same version.

**Requires secret:** `HOMEBREW_TAP_TOKEN` (write access to the tap repository).

### docker-publish.yml

Build and push Docker images to DockerHub, GHCR, or both. Supports dry-run mode (`push: false`)
without requiring registry credentials. Only the newest stable SemVer version moves `latest`;
prereleases and other tags retain their explicit tags. DockerHub publishing requires
`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets.

| Input           | Type    | Default         | Description                                     |
| --------------- | ------- | --------------- | ----------------------------------------------- |
| `image-name`    | string  | **required**    | e.g., `hyperb1iss/git-iris`                     |
| `registry`      | string  | `'docker.io'`   | `docker.io`, `ghcr.io`, or both                 |
| `platforms`     | string  | `'linux/amd64'` | Docker buildx platforms                         |
| `push`          | boolean | `true`          | Actually push (false for dry-run)               |
| `dockerfile`    | string  | `'Dockerfile'`  | Path to Dockerfile                              |
| `build-args`    | string  | `''`            | Docker build arguments                          |
| `version`       | string  | `''`            | Version override (empty = from GITHUB_REF_NAME) |
| `checkout-ref`  | string  | `''`            | Git ref to checkout (empty = caller ref)        |
| `build-context` | string  | `'.'`           | Docker build context directory                  |

---

## Bun workflows

### bun-ci.yml

Installs a Bun workspace from its committed lockfile, runs the repository's unified check script,
then builds it.

| Input               | Type    | Default   | Description                                 |
| ------------------- | ------- | --------- | ------------------------------------------- |
| `bun-version`       | string  | `'1.4.1'` | Exact Bun version to install                |
| `working-directory` | string  | `'.'`     | Workspace root                              |
| `check-script`      | string  | `'check'` | Package script containing all quality gates |
| `build-script`      | string  | `'build'` | Package script producing release artifacts  |
| `run-build`         | boolean | `true`    | Run the build after checks pass             |

### npm-publish.yml

Builds with Bun, then publishes one or more package directories to npm through trusted publishing.
Packages are published in the order listed by `package-dirs`.

| Input          | Type    | Default    | Description                                  |
| -------------- | ------- | ---------- | -------------------------------------------- |
| `bun-version`  | string  | `'1.4.1'`  | Exact Bun version to install                 |
| `package-dirs` | string  | `'.'`      | Newline-separated package directories        |
| `checkout-ref` | string  | `''`       | Git ref to checkout                          |
| `check-script` | string  | `'check'`  | Root release-verification script             |
| `build-script` | string  | `'build'`  | Root package-build script                    |
| `tag`          | string  | `'latest'` | npm distribution tag                         |
| `dry-run`      | boolean | `false`    | Validate package contents without publishing |

Configure npm's trusted publisher against the caller workflow filename, not `npm-publish.yml`.
GitHub's OIDC identity is rooted at the workflow in the consuming repository.

---

## Monorepo workflows

### moon-ci.yml

Polyglot moonrepo workspace CI (Node + Python) with uv + pnpm. Installs proto toolchain, removes
shadowing proto shims so the native setup-\* installs win, and caches `.moon/cache` (save-if-main).

| Input            | Type    | Default   | Description                                   |
| ---------------- | ------- | --------- | --------------------------------------------- |
| `system-deps`    | string  | `''`      | apt packages to install                       |
| `uv-sync`        | boolean | `false`   | Run `uv sync` before tasks                    |
| `uv-sync-args`   | string  | `''`      | Extra uv sync args (e.g., `--all-extras`)     |
| `env-vars`       | string  | `''`      | `KEY=VALUE` lines injected into `$GITHUB_ENV` |
| `moon-commands`  | string  | `''`      | Newline-separated moon commands (preferred)   |
| `moon-tasks`     | string  | `'check'` | Space-separated tasks for `moon ci` (compat)  |
| `node-version`   | string  | `'24'`    | Node.js version                               |
| `python-version` | string  | `'3.13'`  | Python version                                |
| `pnpm-version`   | string  | `''`      | Project pin, or pnpm 10 when unpinned         |

**Command resolution:** If `moon-commands` is set, each line is executed via `bash -c` (must start
with `moon`). If empty, falls back to `moon ci ${{ inputs.moon-tasks }}`.

---

## Versioning

The `v2` tag advances only after repository CI succeeds for the exact main-branch commit being
promoted. Promotion targets v2 explicitly and never selects a tag by its numeric rank. Existing
`@v1` consumers remain on their frozen revision until they migrate.

Removing an input, changing a default, or changing outputs requires a new major version. Additive
inputs and compatible fixes can ship on the existing major. Internal action upgrades still need
compatibility review, especially when upstream changes defaults.

## Development

Run `just setup` to install the locked npm and uv development tools, then `just check` before
opening a PR. Local checks cover Prettier, actionlint, shellcheck, Ruff, ty, and pytest behavior
fixtures. CI also runs a Bun consumer and builds, downloads, installs, and executes a Python
distribution without a source checkout. Tag promotion waits for `lint`, `test`, `smoke`,
`python-smoke`, and `verify-python-smoke`. Run `just format` to format YAML and Markdown. Test
integrations by pointing a consumer at your branch or commit SHA before adopting a new major.

The workflows are the source of truth for action pins. Most actions follow upstream major tags;
`astral-sh/setup-uv` uses the exact `v10.0.1` release. Node 24 and Python 3.13 remain compatibility
defaults. pnpm follows the project pin, with version 10 as the fallback for unpinned projects.
Callers can select newer runtimes through the documented inputs. Bun defaults to 1.4.1.

## License

[Apache 2.0](LICENSE). Built by [Hyperbliss Technologies](https://hyperbliss.tech).
