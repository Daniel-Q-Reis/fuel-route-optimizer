#!/bin/bash
set -e

echo "🔧 Configuring DevContainer..."

# Configure Git globally with defaults
# Note: These are fallbacks. VS Code may sync your local git config.
git config --global user.name "Daniel de Queiroz Reis"
git config --global user.email "danielqreis@gmail.com"
git config --global init.defaultBranch main
git config --global --add safe.directory '/workspaces/*'

echo "✅ Git configured"

# Fix .git permissions for non-root user
if [ -d ".git" ]; then
    sudo chown -R $(whoami) .git/
    chmod -R u+w .git/
    echo "✅ Git permissions fixed"
fi

# Install and configure pre-commit
echo "🔧 Setting up pre-commit..."
pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type pre-push || echo "⚠️  Pre-commit install failed - continuing anyway"

echo "🎉 DevContainer setup complete!"
