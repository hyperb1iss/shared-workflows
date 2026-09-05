# ⚙️ shared-workflows

# Format all YAML and Markdown
format:
    npm run format
    uv run --locked ruff format scripts tests

# Check formatting without writing
format-check:
    npm run format:check
    uv run --locked ruff format --check scripts tests

# Validate workflows against the GitHub Actions schema
lint:
    uv run --locked python scripts/lint_workflows.py
    shellcheck scripts/*.sh
    uv run --locked ruff check scripts tests
    uv run --locked ty check scripts tests

# Execute workflow scripts against isolated regression fixtures
test:
    uv run --locked pytest

# Install the locked development tools
setup:
    npm ci --ignore-scripts
    uv sync --locked

# Everything CI runs
check: format-check lint test
