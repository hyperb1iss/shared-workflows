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
  moon-ci.yml                # moonrepo workspace CI
docs/                        # Documentation
  HANDOFF.md                 # Implementation guide (start here)
  AUDIT.md                   # Full workflow audit across all projects
```

## Key Design Decisions

- All workflows use `workflow_call` trigger with typed inputs
- Secrets passed via `secrets: inherit` (same org)
- Version pinned via tags (e.g., `@v1`)
- Parameterize differences, don't fork workflows
- Smart defaults: nextest, cargo-deny, change detection, all-features ON by default
- Cache only saved on main branch pushes (save-if pattern)

## Action Versions (pinned)

```
actions/checkout@v6          dtolnay/rust-toolchain@stable
actions/setup-node@v6        Swatinem/rust-cache@v2
actions/setup-python@v5      dorny/paths-filter@v3
actions/configure-pages@v5   taiki-e/install-action@v2
actions/upload-pages-artifact@v3  EmbarkStudios/cargo-deny-action@v2
actions/deploy-pages@v4      pnpm/action-setup@v4
actions/upload-artifact@v4   rust-lang/crates-io-auth-action@v1
actions/download-artifact@v4 softprops/action-gh-release@v2
astral-sh/setup-uv@v5       hyperb1iss/git-iris@v2
docker/setup-buildx-action@v3    docker/login-action@v3
docker/build-push-action@v6      moonrepo/setup-toolchain@v0
pypa/gh-action-pypi-publish@release/v1
```

## Workflow Quick Reference

| Workflow               | Key Inputs                                               | Consumers                               |
| ---------------------- | -------------------------------------------------------- | --------------------------------------- |
| `rust-ci`              | workspace, system-deps, nextest, cargo-deny, nightly-fmt | opaline, unifi-cli, git-iris, silkprint |
| `rust-publish`         | crates, publish-delay                                    | opaline, unifi-cli, git-iris, silkprint |
| `rust-release`         | version/bump, workspace-crates, cicd-workflow            | opaline, unifi-cli, git-iris, silkprint |
| `rust-build-artifacts` | binaries, targets, build-packages                        | unifi-cli, git-iris                     |
| `docs-deploy`          | engine (vitepress/mkdocs), docs-dir                      | 6+ repos                                |
| `github-release`       | attach-artifacts, release-notes-run-id                   | 6+ repos                                |
| `homebrew-update`      | formula-name, binary-names                               | unifi-cli, git-iris                     |
| `docker-publish`       | image-name, registry, platforms                          | git-iris, droidmind                     |
| `python-ci`            | python-versions, services, rust-toolchain                | 6+ repos                                |
| `python-publish`       | package-dir                                              | droidmind, sibyl, uchroma, signalrgb-ha |
| `moon-ci`              | moon-tasks                                               | haven, prezzer                          |
