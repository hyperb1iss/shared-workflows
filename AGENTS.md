# shared-workflows

Reusable GitHub Actions workflows for the hyperb1iss project ecosystem.

## Purpose

Centralize CI/CD workflows that are currently duplicated across 15+ repos. Each consuming repo
should go from 50-100+ lines of workflow YAML to ~10 lines calling a shared workflow.

## Repository Structure

```
.github/workflows/           # Reusable workflows (workflow_call triggers)
  rust-ci.yml                # Lint, test, audit for Rust projects
  rust-publish.yml           # Publish to crates.io (trusted publishing)
  rust-release.yml           # Version bump, tag, trigger downstream
  rust-build-artifacts.yml   # Cross-platform binary builds
  docs-deploy.yml            # VitePress/MkDocs → GitHub Pages
  github-release.yml         # Create GitHub Release with git-iris notes
  homebrew-update.yml        # Update homebrew-tap formula
  docker-publish.yml         # Build + push Docker images
  python-ci.yml              # Lint, test for Python (uv) projects
  python-publish.yml         # Publish to PyPI (trusted publishing)
  bun-ci.yml                 # Lint, test, and build Bun workspaces
  npm-publish.yml            # Publish npm packages (trusted publishing)
  moon-ci.yml                # moonrepo workspace CI
  release-tags.yml           # Auto-move major version tag on push
docs/                        # Documentation
```

## Key Design Decisions

- All workflows use `workflow_call` trigger with typed inputs
- Secrets passed via `secrets: inherit` (same org)
- Version pinned via tags (e.g., `@v1`)
- Parameterize differences, don't fork workflows
- Smart defaults: nextest, cargo-deny, change detection, all-features ON by default
- Cache only saved on main branch pushes (save-if pattern)
- Caller inputs reach `run:` blocks through `env:`, never direct `${{ }}` interpolation
- Every workflow declares explicit `permissions:`; job-level blocks replace the top-level one rather
  than merging, so they restate everything they need
- CI gates on prettier **and** actionlint (`just check`) — prettier validates YAML shape, actionlint
  validates the Actions schema, and only the second catches a workflow that parses cleanly but dies
  at startup
- `astral-sh/setup-uv` is pinned to an exact version, not a major tag: upstream announced at v8 that
  it may stop publishing major tags

## Action Versions (pinned)

```
actions/cache/restore@v6
actions/cache/save@v6
actions/checkout@v7
actions/configure-pages@v6
actions/deploy-pages@v5
actions/download-artifact@v8
actions/setup-node@v7
actions/setup-python@v7
actions/upload-artifact@v7
actions/upload-pages-artifact@v5
astral-sh/setup-uv@v9.0.0
docker/build-push-action@v7
docker/login-action@v4
docker/setup-buildx-action@v4
docker/setup-qemu-action@v4
dorny/paths-filter@v4
dtolnay/rust-toolchain@nightly
dtolnay/rust-toolchain@stable
EmbarkStudios/cargo-deny-action@v2
hyperb1iss/git-iris@v2
moonrepo/setup-toolchain@v0
oven-sh/setup-bun@v2
pnpm/action-setup@v6
pypa/gh-action-pypi-publish@release/v1
rust-lang/crates-io-auth-action@v1
softprops/action-gh-release@v3
Swatinem/rust-cache@v2
taiki-e/install-action@v2
```

## Workflow Quick Reference

| Workflow               | Key Inputs                                                 | Consumers                                      |
| ---------------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| `rust-ci`              | workspace, system-deps, nextest, cargo-deny, nightly-fmt   | opaline, unifi-cli, git-iris, silkprint        |
| `rust-publish`         | crates, publish-delay, system-deps                         | opaline, unifi-cli, git-iris, silkprint        |
| `rust-release`         | version/bump, workspace-crates, version-files              | opaline, unifi-cli, git-iris, silkprint        |
| `rust-build-artifacts` | binaries, targets, build-packages                          | unifi-cli, git-iris                            |
| `docs-deploy`          | engine (vitepress/mkdocs), docs-dir                        | sibyl, 6+ repos                                |
| `github-release`       | attach-artifacts, release-notes-run-id                     | 6+ repos                                       |
| `homebrew-update`      | formula-name, binary-names                                 | unifi-cli, git-iris                            |
| `docker-publish`       | image-name, registry, version, checkout-ref                | sibyl, haven, git-iris, droidmind              |
| `python-ci`            | python-version, ruff, pytest, rust-toolchain               | 6+ repos                                       |
| `python-publish`       | package-names, checkout-ref, package-dir                   | sibyl, haven, droidmind, uchroma, signalrgb-ha |
| `bun-ci`               | bun-version, working-directory, check-script, build-script | prezzer                                        |
| `npm-publish`          | bun-version, package-dirs, checkout-ref, tag, dry-run      | prezzer                                        |
| `moon-ci`              | moon-commands, uv-sync, env-vars, system-deps              | haven                                          |
| `release-tags`         | _(internal, no inputs)_                                    | shared-workflows                               |
