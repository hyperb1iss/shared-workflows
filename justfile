# ⚙️ shared-workflows

# Format all YAML and Markdown
format:
    npx prettier --write "**/*.{yml,yaml,md}"

# Check formatting without writing
format-check:
    npx prettier --check "**/*.{yml,yaml,md}"

# Validate workflows against the GitHub Actions schema
lint:
    actionlint .github/workflows/*.yml

# Everything CI runs
check: format-check lint
