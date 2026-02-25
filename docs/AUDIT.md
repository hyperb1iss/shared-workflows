# Workflow Audit — Full Ecosystem

Complete catalog of every GitHub Actions workflow across all hyperb1iss projects. This is the source
of truth for what needs to be unified.

---

## Rust Projects

### opaline (`~/dev/opaline`)

**Repo:** `hyperb1iss/opaline` **Workflows:** `cicd.yml`, `docs.yml`, `release.yml`

#### cicd.yml — "CI/CD"

- **Triggers:** push main, push tags `v*.*.*`, pull_request, workflow_dispatch
- **CI Jobs (push/PR):**
  - `changes` — dorny/paths-filter@v3 (rust: `src/**`, `tests/**`, `examples/**`, `build.rs`,
    `Cargo.toml`, `Cargo.lock`, `deny.toml`, `rust-toolchain.toml`; ci: `.github/workflows/**`,
    `justfile`)
  - `check` — fmt (`cargo fmt --all --check`) + clippy
    (`--all-targets --all-features -- -D warnings`)
  - `test` — cargo-nextest (`cargo nextest run --locked --all-features`) + doc tests
    (`cargo test --doc --locked --all-features`)
  - `deny` — EmbarkStudios/cargo-deny-action@v2
- **CD Jobs (tag only):**
  - `cargo-publish` — rust-lang/crates-io-auth-action@v1 (OIDC) → `cargo publish --locked`
  - `create-release` — hyperb1iss/git-iris@v2 (anthropic, claude-sonnet-4-5-20250929) →
    softprops/action-gh-release@v2
- **System deps:** none
- **Features:** change detection gate, cache save-if main only, nextest, trusted publishing
- **Env:** `CARGO_TERM_COLOR=always`, `RUST_BACKTRACE=1`

#### docs.yml — "Deploy Docs"

- **Triggers:** push main (paths: `docs/**`, `.github/workflows/docs.yml`), workflow_dispatch
- **Stack:** Node 24, pnpm 10, VitePress
- **Jobs:** build → deploy (GitHub Pages with OIDC)
- **Concurrency:** group `pages`, cancel-in-progress false

#### release.yml — "Release"

- **Triggers:** workflow_dispatch (version, bump, dry_run)
- **Flow:** checkout → rust setup → determine version → sed Cargo.toml → cargo update -w → build →
  test → clippy → commit → tag → push → `gh workflow run cicd.yml`
- **Permissions:** contents write, actions write

---

### unifi-cli (`~/dev/unifi-cli`)

**Repo:** `hyperb1iss/unifly` (published name) **Workflows:** `ci.yml`, `cicd.yml`, `docs.yml`,
`release.yml`

#### ci.yml — "CI"

- **Triggers:** push main, pull_request main
- **Jobs:** check → test + clippy (parallel after check), fmt (independent, uses nightly)
- **System deps:** `libdbus-1-dev pkg-config lld` (repeated in EVERY job, 3x)
- **NO change detection** — runs everything on every push
- **NO nextest** — plain `cargo test --workspace --locked`
- **fmt uses nightly:** `cargo +nightly fmt --all -- --check`
- **clippy:** `--workspace --locked -- -D warnings` (NOT `--all-features`, NOT `--all-targets`)

#### cicd.yml — "CI/CD"

- **Triggers:** push tags `v*.*.*`, workflow_dispatch (release_run_id)
- **Jobs:**
  - `build-artifacts` — 4-platform matrix (linux-amd64, linux-arm64 native runner, macos-arm64,
    windows-gnu). Uploads `unifly` + `unifly-tui` binaries.
  - `cargo-publish` — OIDC trusted publishing. Workspace order: `unifly-api` → `unifly-core` with
    30s sleep.
  - `create-release` — downloads artifacts, tries release_run_id notes first, fallback to git-iris.
    Attaches binaries.
  - `update-homebrew` — checksums via curl | shasum, generates Ruby formula inline, pushes to
    `hyperb1iss/homebrew-tap`
- **System deps (Linux only):** `libdbus-1-dev pkg-config lld`
- **Secrets:** ANTHROPIC_API_KEY, HOMEBREW_TAP_TOKEN

#### docs.yml — "Deploy Docs"

- Same pattern as opaline: Node 24, pnpm 10, VitePress, GitHub Pages OIDC

#### release.yml — "Release"

- Same pattern as opaline PLUS:
  - System deps install (`libdbus-1-dev pkg-config lld`)
  - Workspace version: patches workspace package version AND internal dependency pins via sed
  - `cargo build --workspace --release` (not `--all-features`)
  - Generates release notes during release (not just in cicd), uploads as artifact
  - Triggers cicd.yml with `-f release_run_id=${{ github.run_id }}`

---

### git-iris (`~/dev/git-iris`)

**Repo:** `hyperb1iss/git-iris` **Workflows:** `cicd.yml`, `docs.yml`, `release.yml` **Special:**
Also defines `action.yml` (composite GitHub Action)

#### cicd.yml — "CI/CD"

- **Triggers:** push main + tags `v*.*.*`, pull_request main, workflow_dispatch (tag,
  release_run_id)
- **CI Jobs:** `build-and-test` (matrix but only linux-amd64), `docker-build-and-test`
- **CD Jobs (tag only):**
  - `build-artifacts` — 4-platform matrix (same targets as unifi-cli)
  - `build-packages` — .deb (cargo-deb) + .rpm (cargo-generate-rpm) + man page
  - `docker-publish` — docker/build-push-action@v6 to DockerHub (`hyperb1iss/git-iris`)
  - `cargo-publish` — OIDC trusted publishing, single crate
  - `create-release` — downloads all artifacts, git-iris notes (uses `./` self-reference with
    `binary-path`), attaches binaries + packages
  - `update-major-tag` — force-updates `vX` tag for action consumers
  - `update-homebrew` — formula with source build fallback for macOS Intel
  - `update-aur` — KSXGitHub/github-actions-deploy-aur@v3.0.1, generates PKGBUILD
- **NO change detection** — all CI jobs run on every push
- **System deps:** none (pure Rust, no native deps)
- **Secrets:** ANTHROPIC_API_KEY, DOCKER_USERNAME, DOCKER_TOKEN, HOMEBREW_TAP_TOKEN, AUR_SSH_KEY
- **git-iris AI model:** `claude-opus-4-5-20251101` (uses `./` self-reference, different model than
  others)

#### docs.yml — "Deploy Docs"

- Same VitePress/Pages pattern, Node 24, pnpm 10

#### release.yml — "Release"

- Same base pattern PLUS:
  - `skip_changelog` input (boolean)
  - Generates BOTH changelog (`uses: ./` command: changelog, update-file: true) AND release notes
  - Uploads release-notes artifact, passes run_id to cicd.yml
  - Uses `cargo update -p git-iris` (not `-w`)
  - Build: `cargo build --release --locked` (not workspace, not all-features)

---

### silkprint (`~/dev/silkprint`)

**Repo:** `hyperb1iss/silkprint` **Workflows:** `cicd.yml` (was `ci.yml`, renamed), `release.yml`

#### cicd.yml — "CI/CD"

- **Triggers:** push main + tags `v*.*.*`, pull_request
- **CI Jobs:**
  - `changes` — 3-way detection: rust, web, ci
  - `check` — fmt + clippy (`--workspace --all-targets --all-features`)
  - `test` — nextest (`--workspace --locked`) + doc tests
  - `deny` — cargo-deny-action
  - `wasm` — builds `silkprint-wasm` to wasm32-unknown-unknown, runs wasm-bindgen (version-pinned
    from Cargo.lock), patches import.meta.url for Turbopack, optimizes with wasm-opt (binaryen v122)
  - `web` — downloads wasm artifact, copies fonts, pnpm install, typecheck, lint, build
  - `deploy` — same as web but with `GITHUB_PAGES=true NEXT_PUBLIC_BASE_PATH=/silkprint`, deploys to
    Pages
- **CD Jobs (tag only):**
  - `cargo-publish` — OIDC trusted publishing
  - `create-release` — git-iris notes, softprops release
- **Special:** WASM build pipeline, Next.js web app, font copying, Turbopack patching

#### release.yml — "Release"

- Similar base pattern
- Installs rustfmt + clippy + nextest in release job
- Uses nextest for release validation tests

---

## Python Projects

### droidmind (`~/dev/droidmind`)

**Workflows:** `ci-cd.yml`

- **Stack:** Python 3.13, uv, Docker
- **Jobs:** build+lint+test (uv + pytest), docs (MkDocs), deploy docs, release, PyPI publish, Docker
  (GHCR + DockerHub)

### haven (`~/dev/haven`)

**Workflows:** `ci.yml`, `release.yml`, `publish.yml`, `android-release.yml`

- **Stack:** Python 3.13 + Next.js 16 + Kotlin, moonrepo, uv, pnpm
- **Special:** moonrepo workspace, proto shim workaround, Android APK builds

### sibyl (`~/dev/sibyl`)

**Workflows:** `ci.yml`, `docs.yml`, `publish.yml`, `release.yml`

- **Stack:** Python 3.13, FastAPI, FalkorDB, PostgreSQL, uv
- **Special:** Service containers (FalkorDB, pgvector), integration tests

### uchroma (`~/dev/uchroma`)

**Workflows:** `ci.yml`, `docs.yml`, `publish.yml`, `ppa-publish.yml`, `release.yml`

- **Stack:** Python 3.11-3.13, Rust (libhidapi), uv
- **Special:** Multi-Python matrix, Rust toolchain for native deps, Ubuntu PPA publishing

### signalrgb-homeassistant (`~/dev/signalrgb-homeassistant`)

**Workflows:** `ci-cd.yml`

- **Stack:** Python 3.13, uv, HA integration
- **Jobs:** lint, test, release (on tag)

### prezzer (`~/dev/prezzer`)

**Workflows:** `ci.yml`

- **Stack:** Python + Next.js, moonrepo, uv, pnpm
- **Special:** moonrepo workspace CI

---

## Node/Other Projects

### context-eng-demo (`~/dev/context-eng-demo`)

**Workflows:** `deploy.yml`

- **Stack:** Node.js, pnpm, React
- **Jobs:** build → deploy to Pages

### dotfiles (`~/dev/dotfiles`)

**Workflows:** `deploy-docs.yml`, `lint.yml`

- **Stack:** Shell, Lua, Markdown
- **Special:** shellcheck, shfmt, selene, stylua, markdownlint

### hyperbliss.tech (`~/dev/hyperbliss.tech`)

**Workflows:** `ci-cd.yml`

- **Stack:** Node.js, pnpm
- **Jobs:** validate, build, test

### silkcircuit-nvim (`~/dev/silkcircuit-nvim`)

**Workflows:** `ci.yml`, `docs.yml`, `release.yml`

- **Stack:** Lua (Neovim theme)
- **Special:** selene + stylua lint

### silkcircuit-theme (`~/dev/silkcircuit-theme`)

**Workflows:** `ci-cd.yml`

- **Stack:** HACS theme (YAML)
- **Special:** hacs/action@main validation

---

## Universal Action Versions (standardized)

| Action                          | Version            | Notes                      |
| ------------------------------- | ------------------ | -------------------------- |
| actions/checkout                | v6                 | All repos now standardized |
| actions/setup-node              | v6                 | Node 24 everywhere         |
| actions/configure-pages         | v5                 |                            |
| actions/upload-pages-artifact   | v3                 |                            |
| actions/deploy-pages            | v4                 |                            |
| actions/upload-artifact         | v4                 |                            |
| actions/download-artifact       | v4                 |                            |
| dtolnay/rust-toolchain          | @stable / @nightly |                            |
| Swatinem/rust-cache             | v2                 |                            |
| dorny/paths-filter              | v3                 |                            |
| taiki-e/install-action          | v2                 |                            |
| EmbarkStudios/cargo-deny-action | v2                 |                            |
| pnpm/action-setup               | v4                 | pnpm 10                    |
| rust-lang/crates-io-auth-action | v1                 | OIDC trusted publishing    |
| softprops/action-gh-release     | v2                 |                            |
| hyperb1iss/git-iris             | v2                 | AI release notes           |
| docker/setup-buildx-action      | v3                 |                            |
| docker/login-action             | v3                 |                            |
| docker/build-push-action        | v6                 |                            |

---

## Secrets Inventory (across all repos)

| Secret             | Used By                                                   | Purpose                         |
| ------------------ | --------------------------------------------------------- | ------------------------------- |
| ANTHROPIC_API_KEY  | opaline, unifi-cli, git-iris, silkprint + Python projects | git-iris AI release notes       |
| HOMEBREW_TAP_TOKEN | unifi-cli, git-iris                                       | Push to hyperb1iss/homebrew-tap |
| DOCKER_USERNAME    | git-iris, droidmind                                       | DockerHub login                 |
| DOCKER_TOKEN       | git-iris, droidmind                                       | DockerHub login                 |
| AUR_SSH_KEY        | git-iris                                                  | AUR package publishing          |
| GITHUB_TOKEN       | everywhere                                                | Built-in, auto-provided         |

---

## Key Differences Between Rust Projects

| Feature                | opaline           | unifi-cli                    | git-iris                     | silkprint       |
| ---------------------- | ----------------- | ---------------------------- | ---------------------------- | --------------- |
| Change detection       | Yes (2 filters)   | No                           | No                           | Yes (3 filters) |
| System deps            | None              | libdbus-1-dev pkg-config lld | None                         | None            |
| Workspace              | No (single crate) | Yes (4 crates)               | No (single crate)            | Yes (2 crates)  |
| Nextest                | Yes               | No                           | No (CI), Yes (release)       | Yes             |
| --all-features         | Yes               | No                           | No                           | Yes (clippy)    |
| --all-targets          | Yes               | No                           | No                           | Yes             |
| Nightly fmt            | No                | Yes                          | No                           | No              |
| cargo-deny             | Yes               | No                           | No                           | Yes             |
| Cross-platform builds  | No                | Yes (4 targets)              | Yes (4 targets)              | No              |
| Docker                 | No                | No                           | Yes (DockerHub)              | No              |
| Homebrew tap           | No                | Yes                          | Yes                          | No              |
| AUR                    | No                | No                           | Yes                          | No              |
| WASM                   | No                | No                           | No                           | Yes             |
| Publish order          | Single crate      | unifly-api → unifly-core     | Single crate                 | Single crate    |
| git-iris model         | sonnet-4-5        | sonnet-4-5                   | opus-4-5 (self-ref)          | sonnet-4-5      |
| Changelog gen          | No                | No                           | Yes (update-file)            | No              |
| Major tag update       | No                | No                           | Yes (v1, v2)                 | No              |
| Binary artifacts       | No                | unifly + unifly-tui          | git-iris + .deb + .rpm + man | No              |
| Release notes artifact | No                | Yes (from release.yml)       | Yes (from release.yml)       | No              |
