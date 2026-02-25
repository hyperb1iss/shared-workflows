# Implementation Handoff — Shared Workflows

Start here. This document tells you exactly how to build each reusable workflow,
what inputs to parameterize, and how to migrate each consuming repo.

**Prerequisite:** Read `AUDIT.md` for the raw data. This doc is the synthesis.

---

## Table of Contents

1. [How Reusable Workflows Work](#how-reusable-workflows-work)
2. [Workflow Catalog](#workflow-catalog)
3. [Phase 1: Rust Workflows](#phase-1-rust-workflows)
   - [rust-ci.yml](#rust-ciyml)
   - [rust-publish.yml](#rust-publishyml)
   - [rust-release.yml](#rust-releaseyml)
   - [rust-build-artifacts.yml](#rust-build-artifactsyml)
4. [Phase 2: Common Workflows](#phase-2-common-workflows)
   - [docs-deploy.yml](#docs-deployyml)
   - [github-release.yml](#github-releaseyml)
   - [homebrew-update.yml](#homebrew-updateyml)
   - [docker-publish.yml](#docker-publishyml)
5. [Phase 3: Python Workflows](#phase-3-python-workflows)
   - [python-ci.yml](#python-ciyml)
   - [python-publish.yml](#python-publishyml)
6. [Phase 4: Specialty Workflows](#phase-4-specialty-workflows)
   - [moon-ci.yml](#moon-ciyml)
7. [Migration Plan](#migration-plan)
8. [Versioning Strategy](#versioning-strategy)

---

## How Reusable Workflows Work

GitHub Actions reusable workflows use `workflow_call` as the trigger. The calling
repo passes inputs and inherits secrets from the same org.

**Caller (consuming repo):**
```yaml
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:

jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
    with:
      nextest: true
      cargo-deny: true
    secrets: inherit
```

**Callee (this repo):**
```yaml
name: Rust CI
on:
  workflow_call:
    inputs:
      nextest:
        type: boolean
        default: true
    secrets:
      ANTHROPIC_API_KEY:
        required: false
```

**Key constraints:**
- Caller YAML must live in `.github/workflows/` — no subdirectories
- `secrets: inherit` passes all org/repo secrets automatically
- Callee can't trigger other workflows in the CALLER's repo
- Callee permissions are the INTERSECTION of caller + callee permissions
- Maximum 4 levels of nesting (rarely relevant)
- Reusable workflows can define their own `env:` but NOT inherit caller's `env:`

---

## Workflow Catalog

| Workflow | Phase | Consumers (Rust) | Consumers (Other) |
|----------|-------|-------------------|--------------------|
| `rust-ci.yml` | 1 | opaline, unifi-cli, git-iris, silkprint | — |
| `rust-publish.yml` | 1 | opaline, unifi-cli, git-iris, silkprint | — |
| `rust-release.yml` | 1 | opaline, unifi-cli, git-iris, silkprint | — |
| `rust-build-artifacts.yml` | 1 | unifi-cli, git-iris | — |
| `docs-deploy.yml` | 2 | opaline, unifi-cli, git-iris | sibyl, droidmind, uchroma, dotfiles |
| `github-release.yml` | 2 | opaline, unifi-cli, git-iris, silkprint | droidmind, signalrgb-ha |
| `homebrew-update.yml` | 2 | unifi-cli, git-iris | — |
| `docker-publish.yml` | 2 | git-iris | droidmind |
| `python-ci.yml` | 3 | — | droidmind, sibyl, uchroma, signalrgb-ha, haven, prezzer |
| `python-publish.yml` | 3 | — | droidmind, sibyl, uchroma, signalrgb-ha |
| `moon-ci.yml` | 4 | — | haven, prezzer |

---

## Phase 1: Rust Workflows

### rust-ci.yml

The highest-value workflow. Replaces 60-100 lines in each Rust project with ~15.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `change-detection` | boolean | `true` | Enable dorny/paths-filter gating |
| `change-filters` | string | `''` | Extra path filters (YAML, appended to defaults) |
| `system-deps` | string | `''` | apt packages to install (e.g., `libdbus-1-dev pkg-config lld`) |
| `workspace` | boolean | `false` | Use `--workspace` flag on cargo commands |
| `all-features` | boolean | `true` | Use `--all-features` flag |
| `all-targets` | boolean | `true` | Use `--all-targets` for clippy |
| `nextest` | boolean | `true` | Use cargo-nextest (falls back to cargo test if false) |
| `cargo-deny` | boolean | `true` | Run cargo-deny audit |
| `nightly-fmt` | boolean | `false` | Use nightly toolchain for rustfmt |
| `extra-clippy-args` | string | `''` | Additional clippy arguments |
| `rust-toolchain` | string | `'stable'` | Rust toolchain version |

#### Default path filters (always included)

```yaml
rust:
  - 'src/**'
  - 'tests/**'
  - 'examples/**'
  - 'benches/**'
  - 'build.rs'
  - 'Cargo.toml'
  - 'Cargo.lock'
  - 'deny.toml'
  - 'rust-toolchain.toml'
ci:
  - '.github/workflows/**'
  - 'justfile'
  - 'Makefile'
```

#### Jobs

1. **`changes`** — Path filter (skipped if `change-detection: false`, outputs default to `'true'`)
2. **`check`** — `cargo fmt --all --check` + `cargo clippy` (gated on changes)
3. **`test`** — nextest or cargo test + doc tests (gated on changes)
4. **`deny`** — cargo-deny-action (gated on changes, skipped if `cargo-deny: false`)

#### System deps handling

```yaml
- name: Install system dependencies
  if: inputs.system-deps != ''
  run: |
    sudo apt-get update
    sudo apt-get install -y ${{ inputs.system-deps }}
```

This runs in EVERY job that needs it (check, test). It's 3 lines repeated, but
that's fine — the alternative (a separate job with artifact passing) is slower.

#### Caller examples

**opaline** (simplest — all defaults work):
```yaml
jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
    secrets: inherit
```

**unifi-cli** (workspace + system deps + nightly fmt):
```yaml
jobs:
  ci:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@v1
    with:
      system-deps: 'libdbus-1-dev pkg-config lld'
      workspace: true
      all-features: false
      all-targets: false
      nightly-fmt: true
      nextest: false
      cargo-deny: false
      change-detection: false
    secrets: inherit
```

**silkprint** (workspace + extra change filters for web):
```yaml
jobs:
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

---

### rust-publish.yml

Publishes crates to crates.io via OIDC trusted publishing.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `crates` | string | `''` | Space-separated crate names in publish order (empty = single crate) |
| `publish-delay` | number | `30` | Seconds between workspace crate publishes |

#### Permissions

```yaml
permissions:
  id-token: write  # Required for OIDC
```

#### Jobs

Single `publish` job:
1. Checkout + rust setup + cache
2. OIDC auth via `rust-lang/crates-io-auth-action@v1`
3. If `crates` is empty: `cargo publish --locked`
4. If `crates` is set: loop through each, `cargo publish -p $crate --locked`, sleep between

#### Caller examples

**opaline** (single crate):
```yaml
jobs:
  publish:
    if: startsWith(github.ref, 'refs/tags/')
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-publish.yml@v1
    secrets: inherit
```

**unifi-cli** (workspace, ordered):
```yaml
jobs:
  publish:
    if: startsWith(github.ref, 'refs/tags/')
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-publish.yml@v1
    with:
      crates: 'unifly-api unifly-core'
      publish-delay: 30
    secrets: inherit
```

---

### rust-release.yml

Manual version bump → tag → trigger CI/CD. This is the `release.yml` pattern
shared across all 4 Rust projects.

#### Inputs (workflow_dispatch)

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `version` | string | `''` | Explicit version (e.g., `0.2.0`) — overrides bump |
| `bump` | choice | `patch` | `patch` / `minor` / `major` |
| `dry_run` | boolean | `false` | Build + test only, skip publish |

#### Parameterized inputs (workflow_call — set by caller)

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `system-deps` | string | `''` | apt packages for build/test |
| `workspace` | boolean | `false` | Workspace mode |
| `workspace-crates` | string | `''` | Space-separated crate names for workspace version patching |
| `all-features` | boolean | `true` | `--all-features` for build/test/clippy |
| `nextest` | boolean | `true` | Use nextest for release validation |
| `cargo-update-flag` | string | `'-w'` | Flag for `cargo update` (`-w` or `-p crate-name`) |
| `generate-release-notes` | boolean | `false` | Generate + upload release notes artifact |
| `generate-changelog` | boolean | `false` | Update CHANGELOG.md via git-iris |
| `cicd-workflow` | string | `'cicd.yml'` | Downstream workflow to trigger |
| `pass-run-id` | boolean | `false` | Pass `release_run_id` to downstream |

#### Implementation notes

**Dual trigger:** This workflow needs BOTH `workflow_dispatch` (for manual runs)
AND `workflow_call` (for reuse). GitHub supports this — a workflow can have
multiple triggers.

Actually — correction. `workflow_dispatch` and `workflow_call` have separate
input mechanisms and can't coexist cleanly. The better pattern:

**Keep `release.yml` in each repo** as a thin dispatcher that calls the shared
workflow. The `workflow_dispatch` inputs (version, bump, dry_run) live in the
caller. The shared workflow receives them via `workflow_call` inputs.

```yaml
# Caller: each repo's release.yml
name: Release
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Explicit version (e.g., 0.2.0)"
        required: false
        default: ""
      bump:
        description: "Version bump type"
        required: false
        type: choice
        default: "patch"
        options: [patch, minor, major]
      dry_run:
        description: "Dry run"
        required: false
        type: boolean
        default: false

jobs:
  release:
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-release.yml@v1
    with:
      version: ${{ inputs.version }}
      bump: ${{ inputs.bump }}
      dry_run: ${{ inputs.dry_run }}
      # Project-specific overrides:
      workspace: true
      system-deps: 'libdbus-1-dev pkg-config lld'
    secrets: inherit
    permissions:
      contents: write
      actions: write
```

This means `release.yml` stays ~25 lines per repo instead of 80-140. Good tradeoff.

#### Jobs

1. Checkout (fetch-depth: 0, for tag history)
2. Install Rust + cache
3. Install system deps (if set)
4. Configure git (bot user)
5. Determine version (current tag → bump logic)
6. Patch `Cargo.toml` (and workspace deps if `workspace-crates` set)
7. `cargo update`
8. Build + test + clippy
9. Commit version bump
10. Create + push tag
11. (Optional) Generate release notes artifact
12. (Optional) Generate changelog
13. Trigger downstream CI/CD workflow

---

### rust-build-artifacts.yml

Cross-platform binary builds. Used by unifi-cli and git-iris.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `binaries` | string | **required** | Space-separated binary names to extract (e.g., `unifly unifly-tui`) |
| `system-deps` | string | `''` | Linux-only apt packages |
| `targets` | string | `'linux-amd64 linux-arm64 macos-arm64 windows-gnu'` | Space-separated target list |
| `build-packages` | boolean | `false` | Build .deb + .rpm (git-iris only currently) |
| `cargo-build-args` | string | `'--release --locked'` | Extra cargo build arguments |

#### Matrix strategy

| Target | Runner | Rust Target | Binary suffix |
|--------|--------|-------------|---------------|
| `linux-amd64` | `ubuntu-latest` | `x86_64-unknown-linux-gnu` | (none) |
| `linux-arm64` | `ubuntu-24.04-arm` | `aarch64-unknown-linux-gnu` | (none) |
| `macos-arm64` | `macos-latest` | `aarch64-apple-darwin` | (none) |
| `windows-gnu` | `windows-latest` | `x86_64-pc-windows-gnu` | `.exe` |

Each target uploads artifacts named `{binary}-{target}`.

#### Packages job (optional)

If `build-packages: true`:
- Installs `cargo-deb` and `cargo-generate-rpm`
- Builds `.deb` and `.rpm` packages
- Generates man page
- Uploads as `packages` artifact

#### Caller example

**unifi-cli:**
```yaml
jobs:
  build:
    if: startsWith(github.ref, 'refs/tags/')
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-build-artifacts.yml@v1
    with:
      binaries: 'unifly unifly-tui'
      system-deps: 'libdbus-1-dev pkg-config lld'
    secrets: inherit
```

**git-iris:**
```yaml
jobs:
  build:
    if: startsWith(github.ref, 'refs/tags/')
    uses: hyperb1iss/shared-workflows/.github/workflows/rust-build-artifacts.yml@v1
    with:
      binaries: 'git-iris'
      build-packages: true
    secrets: inherit
```

---

## Phase 2: Common Workflows

### docs-deploy.yml

VitePress or MkDocs → GitHub Pages. Identical pattern across 6+ repos.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `docs-dir` | string | `'docs'` | Path to docs directory |
| `node-version` | string | `'24'` | Node.js version |
| `pnpm-version` | string | `'10'` | pnpm version |
| `engine` | string | `'vitepress'` | `vitepress` or `mkdocs` |
| `python-version` | string | `'3.13'` | Python version (MkDocs only) |
| `path-triggers` | string | `'docs/**'` | Paths that trigger the build |

#### Permissions

```yaml
permissions:
  pages: write
  id-token: write  # OIDC for Pages deployment
```

#### Jobs

**VitePress path:**
1. Checkout
2. Setup Node + pnpm
3. `pnpm install` in docs dir
4. `pnpm build`
5. Upload pages artifact
6. Deploy to GitHub Pages

**MkDocs path:**
1. Checkout
2. Setup Python + uv
3. `uv sync` or `uv pip install`
4. `mkdocs build`
5. Upload + deploy

#### Concurrency

```yaml
concurrency:
  group: pages
  cancel-in-progress: false  # Never cancel in-flight deployments
```

#### Caller example

```yaml
name: Deploy Docs
on:
  push:
    branches: [main]
    paths: ['docs/**', '.github/workflows/docs.yml']
  workflow_dispatch:

jobs:
  docs:
    uses: hyperb1iss/shared-workflows/.github/workflows/docs-deploy.yml@v1
    secrets: inherit
```

---

### github-release.yml

Creates a GitHub Release with AI-generated notes via git-iris.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `release-notes-model` | string | `'claude-sonnet-4-5-20250929'` | AI model for git-iris |
| `release-notes-provider` | string | `'anthropic'` | LLM provider |
| `attach-artifacts` | boolean | `false` | Download + attach build artifacts |
| `artifact-pattern` | string | `'*'` | Glob for which artifacts to attach |
| `release-notes-run-id` | string | `''` | Use pre-generated notes from this run |
| `draft` | boolean | `false` | Create as draft release |

#### Permissions

```yaml
permissions:
  contents: write  # Create releases
```

#### Jobs

1. Checkout (fetch-depth: 0)
2. Get previous tag (for release notes range)
3. If `release-notes-run-id` set: download notes artifact from that run
4. Else: generate via `hyperb1iss/git-iris@v2`
5. If `attach-artifacts`: download all matching artifacts
6. Create release via `softprops/action-gh-release@v2`

#### Special case: git-iris self-reference

git-iris uses `uses: ./` to reference itself as a composite action. This
**cannot** be shared — it must remain inline in git-iris's own workflow.
The shared workflow uses `hyperb1iss/git-iris@v2` for all OTHER repos.

#### Caller example

**opaline** (simple):
```yaml
jobs:
  release:
    if: startsWith(github.ref, 'refs/tags/')
    needs: publish
    uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v1
    secrets: inherit
```

**unifi-cli** (with artifacts + pre-generated notes):
```yaml
jobs:
  release:
    if: startsWith(github.ref, 'refs/tags/')
    needs: [publish, build]
    uses: hyperb1iss/shared-workflows/.github/workflows/github-release.yml@v1
    with:
      attach-artifacts: true
      release-notes-run-id: ${{ inputs.release_run_id }}
    secrets: inherit
```

---

### homebrew-update.yml

Updates the Homebrew formula in `hyperb1iss/homebrew-tap`.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `formula-name` | string | **required** | e.g., `git-iris` or `unifly` |
| `tap-repo` | string | `'hyperb1iss/homebrew-tap'` | Target tap repository |
| `description` | string | **required** | Formula description |
| `homepage` | string | **required** | Formula homepage URL |
| `binary-names` | string | **required** | Space-separated binaries to install |
| `source-build-fallback` | boolean | `false` | Include source build for unsupported archs |

#### Secrets

- `HOMEBREW_TAP_TOKEN` — PAT with write access to homebrew-tap repo

#### Jobs

1. Download release artifacts (linux-amd64, macos-arm64)
2. Compute SHA256 checksums
3. Generate Ruby formula (inline template)
4. Clone homebrew-tap, commit formula, push

---

### docker-publish.yml

Build and push Docker images. Used by git-iris and droidmind.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `image-name` | string | **required** | e.g., `hyperb1iss/git-iris` |
| `registry` | string | `'docker.io'` | `docker.io` or `ghcr.io` or both |
| `platforms` | string | `'linux/amd64'` | Docker buildx platforms |
| `push` | boolean | `true` | Actually push (false for test builds) |

#### Secrets

- `DOCKER_USERNAME` + `DOCKER_TOKEN` (for DockerHub)
- `GITHUB_TOKEN` (for GHCR, auto-provided)

#### Jobs

1. Setup QEMU (if multi-platform)
2. Setup Docker Buildx
3. Login to registries
4. Build + push with `docker/build-push-action@v6`
5. Tag with version + `latest`

---

## Phase 3: Python Workflows

### python-ci.yml

Lint + test for Python projects using the Astral stack (uv, ruff).

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `python-version` | string | `'3.13'` | Python version |
| `python-versions` | string | `''` | Multi-version matrix (e.g., `'3.11 3.12 3.13'`) |
| `ruff` | boolean | `true` | Run ruff lint + format check |
| `pytest` | boolean | `true` | Run pytest |
| `pytest-args` | string | `''` | Extra pytest arguments |
| `system-deps` | string | `''` | apt packages |
| `rust-toolchain` | boolean | `false` | Install Rust (for native deps like uchroma) |
| `services` | string | `''` | Service containers needed (e.g., `falkordb postgres`) |
| `moonrepo` | boolean | `false` | Use moon for task orchestration |

#### Jobs

1. **`lint`** — ruff check + ruff format --check
2. **`test`** — uv sync → pytest (optionally with service containers)

#### Service containers

For projects needing databases (sibyl, haven):
```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    ports: ['6379:6379']
  postgres:
    image: pgvector/pgvector:pg16
    ports: ['5432:5432']
    env:
      POSTGRES_PASSWORD: test
```

Service containers are parameterized by name — the shared workflow includes
definitions for known services and activates them based on the `services` input.

---

### python-publish.yml

Publish to PyPI via trusted publishing (OIDC).

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `package-dir` | string | `'.'` | Directory containing pyproject.toml |

#### Permissions

```yaml
permissions:
  id-token: write  # PyPI OIDC
```

#### Jobs

1. Setup Python + uv
2. `uv build`
3. Publish via `pypa/gh-action-pypi-publish@release/v1`

---

## Phase 4: Specialty Workflows

### moon-ci.yml

moonrepo workspace CI. Used by haven and prezzer.

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `node-version` | string | `'24'` | Node.js version |
| `python-version` | string | `'3.13'` | Python version |
| `pnpm-version` | string | `'10'` | pnpm version |
| `moon-tasks` | string | `'check'` | Space-separated moon tasks to run |

#### Jobs

1. Setup proto (via moonrepo/setup-toolchain)
2. `moon ci` — runs affected tasks

---

## Migration Plan

### Execution Order

Migrate in this order — least complex first to shake out issues early:

| Order | Repo | Complexity | Why this order |
|-------|------|------------|----------------|
| 1 | **opaline** | Low | Simplest Rust project, all defaults work |
| 2 | **silkprint** | Medium | Workspace + WASM (WASM stays inline) |
| 3 | **unifi-cli** | Medium | Workspace + system deps + artifacts |
| 4 | **git-iris** | High | Most CD jobs, self-referencing action, Docker, AUR |
| 5 | **signalrgb-ha** | Low | Simple Python CI |
| 6 | **droidmind** | Medium | Python + Docker + docs |
| 7 | **sibyl** | Medium | Python + service containers |
| 8 | **uchroma** | High | Multi-Python + Rust native deps + PPA |
| 9 | **haven** | High | moonrepo + Python + Node + Android |
| 10 | **prezzer** | Medium | moonrepo + Python + Node |

### Per-Repo Migration Steps

For each repo:

1. **Create a branch** — `chore/shared-workflows`
2. **Replace workflow contents** — swap inline jobs with `uses:` calls
3. **Keep project-specific jobs inline** — e.g., silkprint's WASM build, git-iris's AUR/major-tag
4. **Test on the branch** — push to trigger CI, verify all jobs run
5. **Merge** — once green, merge to main
6. **Verify tag flow** — do a dry-run release to verify CD path

### What stays inline (never shared)

Some things are too project-specific to share:

| Repo | Inline job | Reason |
|------|-----------|--------|
| silkprint | WASM build + web build + deploy | Highly custom pipeline |
| git-iris | `update-major-tag` | Only git-iris is a GitHub Action |
| git-iris | `update-aur` | Only git-iris publishes to AUR |
| git-iris | Self-referencing release notes | Uses `./` composite action |
| haven | Android APK build | Kotlin/Gradle, unique to haven |

### What gets normalized (currently inconsistent)

| Issue | Current state | Shared workflow standard |
|-------|--------------|--------------------------|
| Change detection | opaline + silkprint: yes; others: no | Default ON, opt-out |
| Nextest | opaline + silkprint: yes; others: no | Default ON, opt-out |
| `--all-features` | opaline + silkprint: yes; others: no | Default ON, opt-out |
| `--all-targets` | opaline + silkprint: yes; others: no | Default ON, opt-out |
| cargo-deny | opaline + silkprint: yes; others: no | Default ON, opt-out |
| Nightly fmt | Only unifi-cli: yes | Default OFF, opt-in |
| Cache save-if | Only opaline: main-only | Always: save-if main only |

This means unifi-cli and git-iris will get BETTER CI for free just by
migrating — they'll pick up nextest, change detection, all-features, and
cargo-deny without any extra work.

---

## Versioning Strategy

### Tagging

Use major version tags (`v1`, `v2`) with full semver tags (`v1.0.0`, `v1.1.0`):

```bash
git tag v1.0.0
git tag -f v1       # Points to same commit as v1.0.0
git push origin v1.0.0
git push origin v1 --force
```

Callers use `@v1` for automatic minor/patch updates. Only bump to `v2` for
breaking input changes.

### What counts as breaking

- Removing an input
- Changing an input's default value
- Changing job names (callers may use `needs:` on them)
- Changing output names

### What's non-breaking

- Adding new optional inputs
- Adding new jobs
- Updating action versions within the workflow
- Bug fixes

### Release process

1. Make changes on a branch
2. Test by pointing a consuming repo at the branch: `uses: hyperb1iss/shared-workflows/.github/workflows/rust-ci.yml@branch-name`
3. Merge to main
4. Tag with semver + update major tag
5. Consuming repos automatically get the update via `@v1`

---

## Implementation Checklist

### Phase 1 — Rust (do first)

- [ ] Create `.github/workflows/rust-ci.yml` with all inputs from spec
- [ ] Create `.github/workflows/rust-publish.yml`
- [ ] Create `.github/workflows/rust-release.yml`
- [ ] Create `.github/workflows/rust-build-artifacts.yml`
- [ ] Tag `v1.0.0` + `v1`
- [ ] Migrate opaline (test case)
- [ ] Migrate silkprint
- [ ] Migrate unifi-cli
- [ ] Migrate git-iris

### Phase 2 — Common

- [ ] Create `.github/workflows/docs-deploy.yml`
- [ ] Create `.github/workflows/github-release.yml`
- [ ] Create `.github/workflows/homebrew-update.yml`
- [ ] Create `.github/workflows/docker-publish.yml`
- [ ] Migrate docs workflows across all repos
- [ ] Migrate release note generation

### Phase 3 — Python

- [ ] Create `.github/workflows/python-ci.yml`
- [ ] Create `.github/workflows/python-publish.yml`
- [ ] Migrate signalrgb-homeassistant (simplest)
- [ ] Migrate droidmind
- [ ] Migrate sibyl
- [ ] Migrate uchroma

### Phase 4 — Specialty

- [ ] Create `.github/workflows/moon-ci.yml`
- [ ] Migrate haven
- [ ] Migrate prezzer

---

## Quick Reference: Env + Concurrency Patterns

All Rust workflows should set:
```yaml
env:
  CARGO_TERM_COLOR: always
  RUST_BACKTRACE: 1
```

Concurrency for CI:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Concurrency for releases (never cancel):
```yaml
concurrency:
  group: release
  cancel-in-progress: false
```

Concurrency for Pages (never cancel):
```yaml
concurrency:
  group: pages
  cancel-in-progress: false
```

## Quick Reference: Standardized Action Versions

Always use these — no exceptions:

```yaml
actions/checkout@v6
actions/setup-node@v6
actions/configure-pages@v5
actions/upload-pages-artifact@v3
actions/deploy-pages@v4
actions/upload-artifact@v4
actions/download-artifact@v4
dtolnay/rust-toolchain@stable       # or @nightly
Swatinem/rust-cache@v2
dorny/paths-filter@v3
taiki-e/install-action@v2
EmbarkStudios/cargo-deny-action@v2
pnpm/action-setup@v4
rust-lang/crates-io-auth-action@v1
softprops/action-gh-release@v2
hyperb1iss/git-iris@v2
docker/setup-buildx-action@v3
docker/login-action@v3
docker/build-push-action@v6
```
