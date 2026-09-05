# ⚙️ shared-workflows

# Format all YAML and Markdown
format:
    npm run format
    uv run --locked ruff format tests

# Check formatting without writing
format-check:
    npm run format:check
    uv run --locked ruff format --check tests

# Validate workflows against the GitHub Actions schema
lint:
    actionlint .github/workflows/*.yml
    shellcheck scripts/*.sh
    uv run --locked ruff check tests
    uv run --locked ty check tests

# Execute workflow scripts against isolated regression fixtures
test:
    uv run --locked pytest

# Install the locked development tools
setup:
    npm ci --ignore-scripts
    uv sync --locked

# Everything CI runs
check: format-check lint test
