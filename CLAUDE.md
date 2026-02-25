# shared-workflows

Reusable GitHub Actions workflows for the hyperb1iss project ecosystem.

## Purpose

Centralize CI/CD workflows that are currently duplicated across 15+ repos. Each consuming repo should go from 50-100+ lines of workflow YAML to ~10 lines calling a shared workflow.

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
- Start with Rust workflows, expand to Python/Node later
