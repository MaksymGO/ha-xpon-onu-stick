# Development scripts

Run these commands from the repository root.

| Script | Use it to |
| --- | --- |
| [`test.sh`](test.sh) | Set up the test environment, run every check, and optionally read a real stick. |
| [`card.sh`](card.sh) | Preview, test, and screenshot the dashboard card in a local browser. |

## Set up and run the checks

Use **Python 3.14.2 or newer in the 3.14 series** for the pinned Home Assistant test environment. For the first run:

```sh
./scripts/test.sh --setup
```

`--setup` creates `.venv` if needed and installs `requirements-dev.txt`. If Python has a different executable path, use `PYTHON=/path/to/python3.14 ./scripts/test.sh --setup`. A normal run reuses the environment:

```sh
./scripts/test.sh
```

The script checks HACS metadata, repository layout, translations, brand images, installed dependencies, lint, formatting, and the complete test suite. Tests cover status boundaries, ONU state descriptions, shared polling, options form display, saving or clearing module-specific limits, and the dashboard card. It stops at the first failing check and returns a nonzero exit code. Full output is saved to `.test-results/test-*.log`, including failed runs.

## Test the real stick

To run all checks and then read current Device Status and PON Status values from this computer, pass your ONU management address with `--host`. There is no default address. Replace the example `http://onu.example` below with your device's address:

```sh
./scripts/test.sh --live --host http://onu.example
```

If the stick requires authentication:

```sh
./scripts/test.sh --live --host http://onu.example --username YOUR_USERNAME
```

The script prompts privately for the password, then prints all 16 readings as JSON. Passwords are not passed as command-line arguments or saved in the test log. The live readings themselves are included in the log. A connection, authentication, or parsing failure makes the script fail. Use `./scripts/test.sh --help` for all options.

## Preview and test the dashboard card

`card.sh` uses the environment that `./scripts/test.sh --setup` creates.

Open an interactive preview of the card:

```sh
./scripts/card.sh debug
```

The preview runs at `http://127.0.0.1:8765` and reloads when you save the card or its translations. Switch between sample scenarios (healthy, weak signal, problems, unreachable, and no stick), light and dark themes, and card widths. You can also simulate a new poll, change options in the card editor, and see the YAML and click events it produces.

Run the card's UI tests in a headless browser:

```sh
./scripts/card.sh test
```

If a test fails, the script saves a screenshot to `.test-results/card-ui-failure.png`. `./scripts/test.sh` also runs these tests when a browser is available.

Regenerate the README images of the card in `docs/screenshots/`:

```sh
./scripts/card.sh screenshots
```

The preview uses sample readings and stand-ins for Home Assistant's frontend, so it never contacts an ONU or Home Assistant. `test` and `screenshots` need Chrome, Edge, Chromium, or Brave. Set `CHROME_PATH` to choose a browser.

The preview and the UI tests live in [`tools/card/`](../tools/card/). Add sample readings to `scenarios.js` and tests to `ui-tests.js`. [`tools/card_ui.py`](../tools/card_ui.py) serves the preview and drives the browser.
