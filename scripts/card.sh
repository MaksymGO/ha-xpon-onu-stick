#!/usr/bin/env bash
# Debug, test, or screenshot the dashboard card in a local browser.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
    cat <<'EOF'
Usage: ./scripts/card.sh COMMAND [options]

  debug        Open the interactive card preview. It reloads when the card changes.
               Options: --port PORT (default 8765), --no-open
  test         Run the card's UI tests in a headless browser.
               Options: --json
  screenshots  Regenerate the README images in docs/screenshots/.
               Options: --output DIR

The preview uses sample readings and never contacts an ONU or Home Assistant.
test and screenshots need Chrome, Edge, Chromium, or Brave. Set CHROME_PATH to
choose a browser.
EOF
}

case "${1:-}" in
    debug|test|screenshots) ;;
    -h|--help|"") usage; exit 0 ;;
    *) printf 'Unknown command: %s\n' "$1" >&2; usage >&2; exit 2 ;;
esac

TEST_PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$TEST_PYTHON" ]]; then
    printf '%s\n' 'Test environment missing. Run ./scripts/test.sh --setup first.' >&2
    exit 1
fi
exec "$TEST_PYTHON" tools/card_ui.py "$@"
