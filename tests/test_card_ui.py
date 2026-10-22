"""Run the dashboard card's UI tests and screenshots in a local headless browser."""

import asyncio
import json
import struct
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tools.card_ui import find_browser, server_url, start_server

CARD_UI = Path(__file__).resolve().parents[1] / "tools/card_ui.py"
needs_browser = pytest.mark.skipif(
    find_browser() is None, reason="needs Chrome, Edge, Chromium, or Brave"
)


async def run_card_ui(*args: str) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(CARD_UI),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with asyncio.timeout(120):
            stdout, stderr = await process.communicate()
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    return process.returncode, stdout.decode(), stderr.decode()


@needs_browser
async def test_card_ui_tests_pass():
    returncode, stdout, stderr = await run_card_ui("test", "--json")
    results = json.loads(stdout) if stdout else []
    failures = [f"{result['name']}: {result['error']}" for result in results if not result["ok"]]
    assert results, stderr
    assert returncode == 0 and not failures, "\n".join(failures)


@needs_browser
async def test_screenshots_render_both_themes(tmp_path):
    returncode, _, stderr = await run_card_ui("screenshots", "--output", str(tmp_path))
    assert returncode == 0, stderr
    for theme in ("light", "dark"):
        header = (tmp_path / f"dashboard-card-{theme}.png").read_bytes()[:24]
        assert header.startswith(b"\x89PNG")
        width, height = struct.unpack(">II", header[16:24])
        # A 500 px card with 24 px padding, captured at 2x.
        assert width == 1096 and height > 1000


def test_preview_server_only_serves_card_files():
    server = start_server()
    base = server_url(server)

    def status(path: str) -> int:
        try:
            with urllib.request.urlopen(base + path) as response:
                return response.status
        except urllib.error.HTTPError as err:
            return err.code

    try:
        assert status("/tools/card/preview.html") == 200
        assert status("/custom_components/xpon_onu_stick/frontend/xpon-onu-stick-card.js") == 200
        assert status("/tools/card/../../.git/config") == 404
        assert status("/tools/card/%2e%2e/%2e%2e/README.md") == 404
        assert status("/tools/check_status.py") == 404
    finally:
        server.shutdown()
        server.server_close()
