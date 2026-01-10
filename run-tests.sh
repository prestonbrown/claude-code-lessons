#!/usr/bin/env bash
# Self-contained test runner - manages venv and dependencies automatically
#
# Usage: ./run-tests.sh [mode] [pytest-args...]
#
# Modes:
#   fast        Unit tests only, parallel (default)
#   full        All tests, parallel
#   tui         TUI tests only, parallel
#   integration Integration tests only
#
# Examples:
#   ./run-tests.sh              # Fast mode (unit tests)
#   ./run-tests.sh full         # All tests
#   ./run-tests.sh fast -v      # Verbose unit tests
#   ./run-tests.sh full -k foo  # All tests matching 'foo'
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Create venv if missing
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install/update deps if requirements changed
if [[ "$SCRIPT_DIR/requirements-dev.txt" -nt "$VENV_DIR/.deps-installed" ]]; then
    echo "Installing dependencies..."
    pip install -q -r "$SCRIPT_DIR/requirements-dev.txt"
    touch "$VENV_DIR/.deps-installed"
fi

# Parse mode argument
MODE="${1:-fast}"
case "$MODE" in
    full)
        shift
        echo "Running full test suite (parallel)..."
        python -m pytest -n auto "$@"
        ;;
    tui)
        shift
        echo "Running TUI tests (parallel)..."
        python -m pytest -n auto tests/test_tui/ "$@"
        ;;
    integration)
        shift
        echo "Running integration tests..."
        python -m pytest tests/test_integration.py "$@"
        ;;
    fast)
        shift
        echo "Running fast tests (parallel, no TUI/integration)..."
        python -m pytest -n auto -m "not integration and not tui" "$@"
        ;;
    *)
        # Not a mode keyword - pass everything through as fast mode
        echo "Running fast tests (parallel, no TUI/integration)..."
        python -m pytest -n auto -m "not integration and not tui" "$@"
        ;;
esac
