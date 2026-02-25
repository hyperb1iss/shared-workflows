# ✨ shared-workflows

# Format all YAML and Markdown
format:
    npx prettier --write "**/*.{yml,yaml,md}"

# Check formatting without writing
format-check:
    npx prettier --check "**/*.{yml,yaml,md}"
