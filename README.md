<h1 align="center">
  <br>
  ⚙️ shared-workflows
  <br>
</h1>

<p align="center">
  <strong>Reusable GitHub Actions for the hyperb1iss ecosystem</strong><br>
  <sub>✦ 12 workflows · 15+ consumers · one source of truth ✦</sub>
</p>

<p align="center">
  <a href="https://github.com/hyperb1iss/shared-workflows/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/hyperb1iss/shared-workflows/ci.yml?branch=main&style=for-the-badge&logo=github&logoColor=white&label=CI&color=e135ff" alt="CI">
  </a>
  <a href="https://github.com/hyperb1iss/shared-workflows">
    <img src="https://img.shields.io/badge/GitHub_Actions-Reusable-80ffea?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-Apache_2.0-50fa7b?style=for-the-badge" alt="License">
  </a>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#how-to-use-these-workflows">How To Use</a> •
  <a href="#rust-workflows">Rust</a> •
  <a href="#python-workflows">Python</a> •
  <a href="#common-workflows">Common</a> •
  <a href="#monorepo-workflows">Monorepo</a> •
  <a href="#versioning">Versioning</a>
</p>

---

## Overview

Every repo in the hyperb1iss ecosystem was carrying 50–150 lines of duplicated CI/CD YAML. Same
patterns, same action versions, slightly different flags. **shared-workflows** collapses all of that
into reusable `workflow_call` workflows that each consumer invokes in ~10 lines.

> _One repo to rule them all. Bump an action version once, every project gets it._

## How To Use These Workflows

### The Pattern

Every workflow in this repo is a **reusable workflow** triggered via `workflow_call`. A consuming
repo calls it with `uses:` in its own workflow file:

```yaml
# In the consuming repo: .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
    with:
      workspace: true # override defaults as needed
    secrets: inherit # passes all org/repo secrets
```

### Rules

1. **Caller YAML must live in `.github/workflows/`** — no subdirectories
2. **Always use `secrets: inherit`** — passes all org/repo secrets automatically
3. **Pin to `@v1`** — gets automatic minor/patch updates, no breaking changes
4. **Override only what you need** — smart defaults are ON for everything
5. **Keep project-specific jobs inline** — only use shared workflows for common patterns

### Workflow Catalog

| Workflow                  | Phase    | Description                             |
| ------------------------- | -------- | --------------------------------------- |
| 🦀 `rust-ci`              | Rust     | Fmt, clippy, nextest, cargo-deny        |
| 📦 `rust-publish`         | Rust     | Publish to crates.io (OIDC)             |
| 🏷️ `rust-release`         | Rust     | Version bump → tag → trigger downstream |
| 🔨 `rust-build-artifacts` | Rust     | Cross-platform binaries (4 targets)     |
| 📖 `docs-deploy`          | Common   | VitePress / MkDocs → GitHub Pages       |
| 🎯 `github-release`       | Common   | GitHub Release with git-iris AI notes   |
| 🍺 `homebrew-update`      | Common   | Update homebrew-tap formula             |
| 🐳 `docker-publish`       | Common   | Build + push Docker images              |
| 🐍 `python-ci`            | Python   | Ruff lint, pytest, multi-version matrix |
| 📦 `python-publish`       | Python   | Publish to PyPI (OIDC)                  |
| 🌙 `moon-ci`              | Monorepo | moonrepo workspace CI                   |
| 🏷️ `release-tags`         | Internal | Auto-move major version tag on push     |

### Typical CI/CD Pipeline (Rust)

A full Rust project pipeline composes these workflows:

```yaml
# .github/workflows/ci.yml — runs on every push/PR
jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
    secrets: inherit
```

```yaml
# .github/workflows/cicd.yml — runs on tag push
jobs:
  publish:
    if: startsWith(github.ref, 'refs/tags/')
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-publish.yml@v1
    secrets: inherit

  build:
    if: startsWith(github.ref, 'refs/tags/')
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-build-artifacts.yml@v1
    with:
      binaries: 'my-binary'
    secrets: inherit

  release:
    needs: [publish, build]
    uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v1
    with:
      attach-artifacts: true
    secrets: inherit
```

```yaml
# .github/workflows/release.yml — manual trigger
on:
  workflow_dispatch:
    inputs:
      version: { type: string, default: '' }
      bump: { type: choice, default: 'patch', options: [patch, minor, major] }
      dry_run: { type: boolean, default: false }

jobs:
  release:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-release.yml@v1
    with:
      version: ${{ inputs.version }}
      bump: ${{ inputs.bump }}
      dry_run: ${{ inputs.dry_run }}
    secrets: inherit
    permissions:
      contents: write
      actions: write
```

### Typical CI/CD Pipeline (Python)

```yaml
# .github/workflows/ci.yml
jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/python-ci.yml@v1
    secrets: inherit
```

```yaml
# .github/workflows/publish.yml — runs on tag push
jobs:
  publish:
    if: startsWith(github.ref, 'refs/tags/')
    uses: hyperb1iss/shared-workflows/.github/workflows/python-publish.yml@v1
    secrets: inherit
```

---

## Rust Workflows

### rust-ci.yml

The highest-value workflow. Replaces 60–100 lines per Rust project.

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

**Jobs:** `changes` → `check` (fmt + clippy) → `test` (nextest + doc tests) → `deny`

**Examples:**

```yaml
# Simplest — all defaults work
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
  secrets: inherit

# Workspace with system deps and nightly fmt
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
  with:
    system-deps: 'libdbus-1-dev pkg-config lld'
    workspace: true
    nightly-fmt: true
    nextest: false
    cargo-deny: false
    change-detection: false
  secrets: inherit

# Workspace with extra change filters for web assets
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
  with:
    workspace: true
    change-filters: |
      web:
        - 'web/**'
        - 'fonts/**'
  secrets: inherit
```

### rust-publish.yml

Publishes to crates.io via OIDC trusted publishing. No tokens to manage.

| Input           | Type   | Default | Description                         |
| --------------- | ------ | ------- | ----------------------------------- |
| `crates`        | string | `''`    | Space-separated crates in order     |
| `publish-delay` | number | `30`    | Seconds between workspace publishes |
| `system-deps`   | string | `''`    | apt packages needed for build       |

**Examples:**

```yaml
# Single crate
publish:
  uses: hyperb1iss/shared-workflows/.github/workflows/rust-publish.yml@v1
  secrets: inherit

# Workspace with ordered publishes
publish:
  uses: hyperb1iss/shared-workflows/.github/workflows/rust-publish.yml@v1
  with:
    crates: 'my-api my-core'
    publish-delay: 30
  secrets: inherit
```

### rust-release.yml

Version bump → tag → trigger CI/CD. Each consumer keeps a thin `release.yml` with
`workflow_dispatch` inputs that calls this shared workflow.

| Input                          | Type    | Default      | Description                                         |
| ------------------------------ | ------- | ------------ | --------------------------------------------------- |
| `version`                      | string  | `''`         | Explicit version (overrides bump)                   |
| `bump`                         | string  | `'patch'`    | `patch` / `minor` / `major`                         |
| `dry_run`                      | boolean | `false`      | Build + test only                                   |
| `system-deps`                  | string  | `''`         | apt packages                                        |
| `workspace`                    | boolean | `false`      | Workspace mode                                      |
| `workspace-crates`             | string  | `''`         | Crates for version patching                         |
| `all-features`                 | boolean | `true`       | `--all-features` for build/test                     |
| `nextest`                      | boolean | `true`       | Use nextest for validation                          |
| `generate-release-notes`       | boolean | `false`      | Generate via git-iris                               |
| `generate-changelog`           | boolean | `false`      | Update CHANGELOG.md                                 |
| `cicd-workflow`                | string  | `'cicd.yml'` | Downstream workflow to trigger                      |
| `pass-run-id`                  | boolean | `false`      | Pass release_run_id to downstream                   |
| `patch-workspace-dep-versions` | boolean | `false`      | Patch version pins for path deps in root Cargo.toml |
| `version-files`                | string  | `''`         | Extra files to patch (JSON, YAML frontmatter)       |

### rust-build-artifacts.yml

Cross-platform binary builds with a 4-target matrix.

| Input              | Type    | Default                                             | Description             |
| ------------------ | ------- | --------------------------------------------------- | ----------------------- |
| `binaries`         | string  | **required**                                        | Binary names to extract |
| `system-deps`      | string  | `''`                                                | Linux apt packages      |
| `targets`          | string  | `'linux-amd64 linux-arm64 macos-arm64 windows-gnu'` | Build targets           |
| `build-packages`   | boolean | `false`                                             | Build .deb + .rpm       |
| `cargo-build-args` | string  | `'--release --locked'`                              | Extra build args        |

**Matrix:**

| Target        | Runner             | Rust Target                 |
| ------------- | ------------------ | --------------------------- |
| `linux-amd64` | `ubuntu-latest`    | `x86_64-unknown-linux-gnu`  |
| `linux-arm64` | `ubuntu-24.04-arm` | `aarch64-unknown-linux-gnu` |
| `macos-arm64` | `macos-latest`     | `aarch64-apple-darwin`      |
| `windows-gnu` | `windows-latest`   | `x86_64-pc-windows-gnu`     |

**Example:**

```yaml
build:
  uses: hyperb1iss/shared-workflows/.github/workflows/rust-build-artifacts.yml@v1
  with:
    binaries: 'my-cli my-tui'
    system-deps: 'libdbus-1-dev pkg-config'
    build-packages: true
  secrets: inherit
```

---

## Python Workflows

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

> **Need service containers or a version matrix?** Reusable workflows can't attach services
> conditionally. Define services and matrix strategy directly in the caller repo and inline the
> setup there.

**Examples:**

```yaml
# Simple — all defaults
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/python-ci.yml@v1
  secrets: inherit

# With system deps and extra pytest args
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/python-ci.yml@v1
  with:
    system-deps: 'libpq-dev'
    pytest-args: '-x --timeout=60'
  secrets: inherit

# Native Rust extension (needs Rust toolchain)
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/python-ci.yml@v1
  with:
    rust-toolchain: true
  secrets: inherit
```

### python-publish.yml

Publish to PyPI via OIDC trusted publishing. Supports single-package and multi-package workspace
builds.

| Input           | Type   | Default | Description                                         |
| --------------- | ------ | ------- | --------------------------------------------------- |
| `package-dir`   | string | `'.'`   | Directory with pyproject.toml (single-package mode) |
| `package-names` | string | `''`    | Space-separated names for `uv build --package`      |
| `checkout-ref`  | string | `''`    | Git ref to checkout (empty = caller ref)            |

> **OIDC Note:** When using this reusable workflow, configure PyPI trusted publishing to point at
> `hyperb1iss/shared-workflows/.github/workflows/python-publish.yml`, not the caller repo.

**Examples:**

```yaml
# Single package (default)
publish:
  if: startsWith(github.ref, 'refs/tags/')
  uses: hyperb1iss/shared-workflows/.github/workflows/python-publish.yml@v1
  secrets: inherit

# Workspace with multiple packages
publish:
  uses: hyperb1iss/shared-workflows/.github/workflows/python-publish.yml@v1
  with:
    package-names: "sibyl-core sibyl-dev"
    checkout-ref: v0.1.0
  permissions:
    contents: read
    id-token: write
```

---

## Common Workflows

### docs-deploy.yml

VitePress or MkDocs → GitHub Pages with OIDC deployment.

| Input            | Type   | Default       | Description                  |
| ---------------- | ------ | ------------- | ---------------------------- |
| `docs-dir`       | string | `'docs'`      | Path to docs directory       |
| `node-version`   | string | `'24'`        | Node.js version              |
| `pnpm-version`   | string | `'10'`        | pnpm version                 |
| `engine`         | string | `'vitepress'` | `vitepress` or `mkdocs`      |
| `python-version` | string | `'3.13'`      | Python version (MkDocs only) |

**Examples:**

```yaml
# VitePress (default)
docs:
  uses: hyperb1iss/shared-workflows/.github/workflows/docs-deploy.yml@v1
  secrets: inherit

# MkDocs
docs:
  uses: hyperb1iss/shared-workflows/.github/workflows/docs-deploy.yml@v1
  with:
    engine: mkdocs
  secrets: inherit
```

### github-release.yml

Creates a GitHub Release with AI-generated notes from
[git-iris](https://github.com/hyperb1iss/git-iris).

| Input                    | Type    | Default             | Description                      |
| ------------------------ | ------- | ------------------- | -------------------------------- |
| `release-notes-model`    | string  | `'claude-opus-4-7'` | AI model for release notes       |
| `release-notes-provider` | string  | `'anthropic'`       | LLM provider                     |
| `attach-artifacts`       | boolean | `false`             | Attach build artifacts           |
| `artifact-pattern`       | string  | `'*'`               | Glob for artifacts to attach     |
| `release-notes-run-id`   | string  | `''`                | Use pre-generated notes from run |
| `draft`                  | boolean | `false`             | Create as draft release          |

**Examples:**

```yaml
# Simple release with AI notes
release:
  needs: publish
  uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v1
  secrets: inherit

# Release with artifacts from build job
release:
  needs: [publish, build]
  uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v1
  with:
    attach-artifacts: true
  secrets: inherit

# Pre-generated notes from release workflow
release:
  needs: [publish, build]
  uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v1
  with:
    attach-artifacts: true
    release-notes-run-id: ${{ inputs.release_run_id }}
  secrets: inherit
```

### homebrew-update.yml

Auto-updates the formula in [homebrew-tap](https://github.com/hyperb1iss/homebrew-tap) after a
release. Generates CamelCase Ruby class names automatically (e.g., `git-iris` → `GitIris`).

| Input          | Type   | Default                     | Description                  |
| -------------- | ------ | --------------------------- | ---------------------------- |
| `formula-name` | string | **required**                | e.g., `git-iris` or `unifly` |
| `tap-repo`     | string | `'hyperb1iss/homebrew-tap'` | Target tap repository        |
| `description`  | string | **required**                | Formula description          |
| `homepage`     | string | **required**                | Formula homepage URL         |
| `binary-names` | string | **required**                | Space-separated binaries     |

**Artifact contract:** callers must upload one artifact per target, named `binaries-linux-amd64`
and/or `binaries-macos-arm64`, containing the raw binaries at the root. The workflow tars each
artifact itself, uploads the tarball as a release asset, and generates a formula that runs
`bin.install` for each name in `binary-names`.

**Optional support payloads:** if the artifact also contains a top-level `share/` directory
(terminfo, shell integration, man pages, themes, completions) or `etc/` directory (system config),
the generated formula will install them into Homebrew's prefix automatically. Projects shipping only
binaries can ignore this — the install steps are guarded by `Dir.exist?` checks.

**Requires secret:** `HOMEBREW_TAP_TOKEN`

**Example:**

```yaml
homebrew:
  needs: [build, release]
  uses: hyperb1iss/shared-workflows/.github/workflows/homebrew-update.yml@v1
  with:
    formula-name: git-iris
    description: 'AI-powered Git workflow assistant'
    homepage: 'https://github.com/hyperb1iss/git-iris'
    binary-names: 'git-iris'
  secrets: inherit
```

### docker-publish.yml

Build and push Docker images to DockerHub, GHCR, or both. Supports dry-run mode (`push: false`)
without requiring registry credentials.

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

**Examples:**

```yaml
# DockerHub only
docker:
  uses: hyperb1iss/shared-workflows/.github/workflows/docker-publish.yml@v1
  with:
    image-name: hyperb1iss/my-app
  secrets: inherit

# Both registries, multi-platform
docker:
  uses: hyperb1iss/shared-workflows/.github/workflows/docker-publish.yml@v1
  with:
    image-name: hyperb1iss/my-app
    registry: 'docker.io, ghcr.io'
    platforms: 'linux/amd64,linux/arm64'
  secrets: inherit

# GHCR with version override (monorepo publish)
docker-api:
  uses: hyperb1iss/shared-workflows/.github/workflows/docker-publish.yml@v1
  with:
    image-name: hyperb1iss/sibyl-api
    registry: ghcr.io
    dockerfile: apps/api/Dockerfile
    version: v0.1.0
    checkout-ref: v0.1.0
  secrets: inherit
```

---

## Monorepo Workflows

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
| `pnpm-version`   | string  | `'10'`    | pnpm version                                  |

**Command resolution:** If `moon-commands` is set, each line is executed via `bash -c` (must start
with `moon`). If empty, falls back to `moon ci ${{ inputs.moon-tasks }}`.

**Examples:**

```yaml
# Simple — backward-compatible
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/moon-ci.yml@v1
  with:
    moon-tasks: 'check lint test'
  secrets: inherit

# Polyglot with uv sync and explicit commands
ci:
  uses: hyperb1iss/shared-workflows/.github/workflows/moon-ci.yml@v1
  with:
    uv-sync: true
    uv-sync-args: '--all-extras'
    moon-commands: |
      moon run :lint --query "language=[python, javascript]"
      moon run :typecheck --query "language=[python, javascript]"
      moon run :test --query "language=[python, javascript]"
  secrets: inherit
```

> **Need service containers?** Reusable workflows can't attach services conditionally, and
> project-specific service topology (FalkorDB, Temporal, Qdrant, …) doesn't generalize. Define
> services directly in the caller repo and inline the moon setup there.

---

## Versioning

Consumers pin to a major version tag:

```yaml
uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
```

The `release-tags.yml` workflow automatically fast-forwards the highest major version tag (e.g.,
`v1`) to the tip of `main` on every push. Non-breaking changes land immediately for all consumers
without any release ceremony.

**Breaking changes** require manually cutting the next major tag _before_ pushing:

```bash
git tag -a v2 -m "v2: describe the break"
git push origin v2
# Now push the breaking change — release-tags moves v2, v1 stays frozen
```

**Breaking** (bumps major): removing inputs, changing defaults, renaming jobs/outputs.

**Non-breaking** (stays on current major): adding optional inputs, adding jobs, updating internal
action versions, bug fixes.

---

## Development

```bash
# Format all YAML and Markdown
just format

# Check formatting
just format-check
```

### Action Versions (pinned)

All workflows use consistent, pinned action versions:

```
actions/checkout@v6              dtolnay/rust-toolchain@stable
actions/setup-node@v6            Swatinem/rust-cache@v2
actions/setup-python@v6          dorny/paths-filter@v3
actions/configure-pages@v5       taiki-e/install-action@v2
actions/upload-pages-artifact@v4 EmbarkStudios/cargo-deny-action@v2
actions/deploy-pages@v4          pnpm/action-setup@v4
actions/upload-artifact@v7       rust-lang/crates-io-auth-action@v1
actions/download-artifact@v8     softprops/action-gh-release@v2
actions/cache@v4                 hyperb1iss/git-iris@v2
astral-sh/setup-uv@v7           moonrepo/setup-toolchain@v0
docker/setup-buildx-action@v4   docker/login-action@v4
docker/build-push-action@v7     docker/setup-qemu-action@v4
pypa/gh-action-pypi-publish@release/v1
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and run `just format`
4. Test by pointing a consuming repo at your branch:
   ```yaml
   uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@your-branch
   ```
5. Open a PR

---

## ⚖️ License

Licensed under the [Apache License 2.0](LICENSE).

---

<p align="center">
  <a href="https://github.com/hyperb1iss/shared-workflows">
    <img src="https://img.shields.io/github/stars/hyperb1iss/shared-workflows?style=social" alt="Star on GitHub">
  </a>
  &nbsp;&nbsp;
  <a href="https://ko-fi.com/hyperb1iss">
    <img src="https://img.shields.io/badge/Ko--fi-Support%20Development-ff5e5b?logo=ko-fi&logoColor=white" alt="Ko-fi">
  </a>
</p>

<p align="center">
  <sub>
    ✦ Built with obsession by <a href="https://hyperbliss.tech"><strong>Hyperbliss Technologies</strong></a> ✦
  </sub>
</p>
