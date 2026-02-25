<h1 align="center">
  <br>
  ⚙️ shared-workflows
  <br>
</h1>

<p align="center">
  <strong>Reusable GitHub Actions for the hyperb1iss ecosystem</strong><br>
  <sub>✦ 11 workflows · 15+ consumers · one source of truth ✦</sub>
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
  <a href="#workflow-catalog">Catalog</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#rust-workflows">Rust</a> •
  <a href="#python-workflows">Python</a> •
  <a href="#common-workflows">Common</a> •
  <a href="#versioning">Versioning</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## Overview

Every repo in the hyperb1iss ecosystem was carrying 50–150 lines of duplicated CI/CD YAML. Same
patterns, same action versions, slightly different flags. **shared-workflows** collapses all of that
into reusable `workflow_call` workflows that each consumer invokes in ~10 lines.

> _One repo to rule them all. Bump an action version once, every project gets it._

## Workflow Catalog

| Workflow                  | Phase    | Description                             |
| ------------------------- | -------- | --------------------------------------- |
| 🦀 `rust-ci`              | Rust     | Fmt, clippy, nextest, cargo-deny        |
| 📦 `rust-publish`         | Rust     | Publish to crates.io (OIDC)             |
| 🏷️ `rust-release`         | Rust     | Version bump → tag → trigger downstream |
| 🔨 `rust-build-artifacts` | Rust     | Cross-platform binaries (4 targets)     |
| 📖 `docs-deploy`          | Common   | VitePress / MkDocs → GitHub Pages       |
| 🎉 `github-release`       | Common   | GitHub Release with git-iris AI notes   |
| 🍺 `homebrew-update`      | Common   | Update homebrew-tap formula             |
| 🐳 `docker-publish`       | Common   | Build + push Docker images              |
| 🐍 `python-ci`            | Python   | Ruff lint, pytest, multi-version matrix |
| 📦 `python-publish`       | Python   | Publish to PyPI (OIDC)                  |
| 🌙 `moon-ci`              | Monorepo | moonrepo workspace CI                   |

## Quick Start

Call any workflow from your repo's `.github/workflows/` directory:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
    secrets: inherit
```

That's it. All smart defaults are ON — nextest, cargo-deny, change detection, `--all-features`.
Override only what you need:

```yaml
jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
    with:
      system-deps: 'libdbus-1-dev pkg-config lld'
      workspace: true
      nightly-fmt: true
      cargo-deny: false
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

### rust-publish.yml

Publishes to crates.io via OIDC trusted publishing. No tokens to manage.

| Input           | Type   | Default | Description                         |
| --------------- | ------ | ------- | ----------------------------------- |
| `crates`        | string | `''`    | Space-separated crates in order     |
| `publish-delay` | number | `30`    | Seconds between workspace publishes |

### rust-release.yml

Version bump → tag → trigger CI/CD. Each consumer keeps a thin `release.yml` with
`workflow_dispatch` inputs that calls this.

| Input                    | Type    | Default      | Description                       |
| ------------------------ | ------- | ------------ | --------------------------------- |
| `version`                | string  | `''`         | Explicit version (overrides bump) |
| `bump`                   | string  | `'patch'`    | `patch` / `minor` / `major`       |
| `dry_run`                | boolean | `false`      | Build + test only                 |
| `system-deps`            | string  | `''`         | apt packages                      |
| `workspace`              | boolean | `false`      | Workspace mode                    |
| `workspace-crates`       | string  | `''`         | Crates for version patching       |
| `generate-release-notes` | boolean | `false`      | Generate via git-iris             |
| `cicd-workflow`          | string  | `'cicd.yml'` | Downstream workflow to trigger    |

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

---

## Python Workflows

### python-ci.yml

Lint + test using the Astral stack (uv, ruff). Supports multi-version matrices and service
containers for database-backed projects.

| Input             | Type    | Default  | Description                                                |
| ----------------- | ------- | -------- | ---------------------------------------------------------- |
| `python-version`  | string  | `'3.13'` | Python version                                             |
| `python-versions` | string  | `''`     | JSON array for matrix (e.g., `'["3.11", "3.12", "3.13"]'`) |
| `ruff`            | boolean | `true`   | Run ruff lint + format check                               |
| `pytest`          | boolean | `true`   | Run pytest                                                 |
| `pytest-args`     | string  | `''`     | Extra pytest arguments                                     |
| `system-deps`     | string  | `''`     | apt packages                                               |
| `rust-toolchain`  | boolean | `false`  | Install Rust (for native deps)                             |
| `services`        | string  | `''`     | Service containers (`'falkordb postgres'`)                 |

**Jobs:** `lint` (ruff check + format) → `test` / `test-with-services`

### python-publish.yml

Publish to PyPI via OIDC trusted publishing.

| Input         | Type   | Default | Description                   |
| ------------- | ------ | ------- | ----------------------------- |
| `package-dir` | string | `'.'`   | Directory with pyproject.toml |

---

## Common Workflows

### docs-deploy.yml

VitePress or MkDocs → GitHub Pages with OIDC deployment.

```yaml
jobs:
  docs:
    uses: hyperb1iss/shared-workflows/.github/workflows/docs-deploy.yml@v1
    # engine defaults to 'vitepress'
```

### github-release.yml

Creates a GitHub Release with AI-generated notes from
[git-iris](https://github.com/hyperb1iss/git-iris).

```yaml
jobs:
  release:
    needs: [publish, build]
    uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v1
    with:
      attach-artifacts: true
    secrets: inherit
```

### homebrew-update.yml

Auto-updates the formula in [homebrew-tap](https://github.com/hyperb1iss/homebrew-tap) after a
release.

### docker-publish.yml

Build and push Docker images to DockerHub, GHCR, or both.

### moon-ci.yml

moonrepo workspace CI for polyglot projects (Node + Python).

---

## Versioning

Consumers pin to a major version tag:

```yaml
uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
```

**Breaking** (bumps major): removing inputs, changing defaults, renaming jobs/outputs.

**Non-breaking** (stays on current major): adding optional inputs, adding jobs, updating internal
action versions, bug fixes.

---

## Consumers

| Repo                        | Workflows Used                                                                                             |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **opaline**                 | rust-ci, rust-publish, github-release                                                                      |
| **silkprint**               | rust-ci, rust-publish, github-release                                                                      |
| **unifi-cli**               | rust-ci, rust-publish, rust-release, rust-build-artifacts, github-release, homebrew-update                 |
| **git-iris**                | rust-ci, rust-publish, rust-release, rust-build-artifacts, github-release, homebrew-update, docker-publish |
| **droidmind**               | python-ci, python-publish, docs-deploy, docker-publish                                                     |
| **sibyl**                   | python-ci, docs-deploy                                                                                     |
| **uchroma**                 | python-ci, python-publish                                                                                  |
| **signalrgb-homeassistant** | python-ci, python-publish                                                                                  |
| **haven**                   | python-ci, moon-ci                                                                                         |
| **prezzer**                 | python-ci, moon-ci                                                                                         |

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
actions/setup-python@v5          dorny/paths-filter@v3
actions/configure-pages@v5       taiki-e/install-action@v2
actions/upload-pages-artifact@v3 EmbarkStudios/cargo-deny-action@v2
actions/deploy-pages@v4          pnpm/action-setup@v4
actions/upload-artifact@v4       rust-lang/crates-io-auth-action@v1
actions/download-artifact@v4     softprops/action-gh-release@v2
astral-sh/setup-uv@v5           hyperb1iss/git-iris@v2
docker/setup-buildx-action@v3   docker/login-action@v3
docker/build-push-action@v6     moonrepo/setup-toolchain@v0
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
