#!/bin/bash
# setup-uv.sh - Setup script for uv environment with JSPyBridge patches
#
# This script sets up the Python environment and installs Mineflayer plugins
# (JavaScript/Node.js). It does NOT install Minecraft AI plugins (Python),
# which are located in the plugins/ directory and loaded dynamically.

set -e

echo "🔧 Minecraft AI-Python UV Setup"
echo "================================"
echo ""
echo "This script sets up:"
echo "  - Python dependencies (uv)"
echo "  - Mineflayer plugins (JavaScript via npm/JSPyBridge)"
echo ""
echo "Note: Minecraft AI plugins (in plugins/) are Python files that"
echo "      don't need installation - they're loaded dynamically."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv found: $(uv --version)"

# Sync dependencies
echo ""
echo "📦 Installing Python dependencies..."
uv sync

# Get Python version (major.minor)
PYTHON_VERSION=$(uv run python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python version: $PYTHON_VERSION"

# Define paths
JSPY_PATH=".venv/lib/python$PYTHON_VERSION/site-packages/javascript/js"
NODE_MODULES="$JSPY_PATH/node_modules"

# Check if patches have been applied before
VERSION_JS="$NODE_MODULES/mineflayer/lib/version.js"
DEPS_JS="$JSPY_PATH/deps.js"

echo ""
echo "🔍 Checking JSPyBridge patches..."

# Apply deps.js patch (check if already applied)
if grep -q "const resolvedPath = pm.resolve(newpath)" "$DEPS_JS" 2>/dev/null; then
    echo "✅ deps.js already patched"
else
    echo "📝 Applying deps.js patch..."
    # Backup original
    cp "$DEPS_JS" "$DEPS_JS.backup"
    # Apply the patch
    sed -i '' 's/const mod = await import(\[newpath, \.\.\.path\]\.join.*$/const resolvedPath = pm.resolve(newpath)\n  const mod = await import(resolvedPath.href)/' "$DEPS_JS"
    echo "✅ deps.js patched (backup saved to deps.js.backup)"
fi

# For version.js patch, we need to trigger the node_modules creation first
# by running a simple Python import
echo ""
echo "🚀 Triggering JSPyBridge node_modules installation..."
echo "   (This installs Mineflayer plugins via npm)"
uv run python -c "from javascript import require; print('JSPyBridge initialized')" 2>&1 | grep -q "JSPyBridge initialized" || true

# Now check if version.js exists and patch it
if [ -f "$VERSION_JS" ]; then
    if grep -q "1.21.10" "$VERSION_JS"; then
        echo "✅ version.js already patched"
    else
        echo "📝 Applying version.js patch..."
        # Backup original
        cp "$VERSION_JS" "$VERSION_JS.backup"
        # Apply the patch (change 1.21.11 to 1.21.10)
        sed -i '' 's/1\.21\.11/1.21.10/g' "$VERSION_JS"
        echo "✅ version.js patched (backup saved to version.js.backup)"
    fi
else
    echo "⚠️  version.js not found yet. Will be patched on first run."
    echo "   Run this script again after the first 'uv run main.py' if needed."
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "Plugin Systems Status:"
echo "  ✅ Mineflayer plugins (JS): Installed via npm/JSPyBridge"
echo "  ✅ Minecraft AI plugins (Python): Ready in plugins/ directory"
echo ""
echo "To run the bot:"
echo "  source .venv/bin/activate"
echo "  python main.py --agents ./profiles/max.json"
echo ""
echo "Or with uv:"
echo "  uv run python main.py --agents ./profiles/max.json"
echo ""
