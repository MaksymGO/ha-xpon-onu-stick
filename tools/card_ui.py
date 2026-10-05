"""Debug, test, and screenshot the dashboard card in a local browser.

  debug        Serve the interactive preview and open it. It reloads when card files change.
  test         Run the card's UI tests in a headless browser.
  screenshots  Regenerate the README images of the card in light and dark themes.

The preview uses sample readings and stand-ins for Home Assistant's frontend, so
nothing contacts an ONU or Home Assistant. `test` and `screenshots` need a
Chromium-based browser (Chrome, Edge, Chromium, or Brave). Set CHROME_PATH to
choose one.
"""

import argparse
import asyncio
import base64
import contextlib
import json
import os
import posixpath
import re
import shutil
import signal
import sys
import tempfile
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = "/tools/card/preview.html"
# Only the card and its preview are served, never the rest of the repository.
SERVED = ("/tools/card/", "/custom_components/xpon_onu_stick/")
SCREENSHOTS = ROOT / "docs" / "screenshots"
RESULTS = ROOT / ".test-results"
BROWSERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "microsoft-edge-stable",
    "brave-browser",
)
TIMEOUT = 30


def find_browser() -> str | None:
    """Return a Chromium-based browser executable, preferring CHROME_PATH."""
    for candidate in (os.environ.get("CHROME_PATH"), *BROWSERS):
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return shutil.which(candidate) or candidate
    return None


class PreviewHandler(SimpleHTTPRequestHandler):
    """Serve the preview files without caching, so edits show up on reload."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _allowed(self) -> bool:
        path = posixpath.normpath(unquote(urlsplit(self.path).path))
        return path.startswith(SERVED)

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/":
            self.send_response(302)
            self.send_header("Location", PREVIEW)
            self.end_headers()
        elif self._allowed():
            super().do_GET()
        else:
            self.send_error(404)

    def do_HEAD(self) -> None:
        if self._allowed():
            super().do_HEAD()
        else:
            self.send_error(404)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args) -> None:
        pass


def start_server(port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), PreviewHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def server_url(server: ThreadingHTTPServer) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}"


class Browser:
    """A headless browser driven over the Chrome DevTools Protocol."""

    def __init__(self, executable: str) -> None:
        self._executable = executable
        self._next_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._waiters: list[tuple[str, str | None, asyncio.Future]] = []
        self.errors: list[str] = []

    async def __aenter__(self) -> Browser:
        self._profile = tempfile.TemporaryDirectory(prefix="card-ui-", ignore_cleanup_errors=True)
        self._process = await asyncio.create_subprocess_exec(
            self._executable,
            "--headless=new",
            "--remote-debugging-port=0",
            f"--user-data-dir={self._profile.name}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--hide-scrollbars",
            "--mute-audio",
            # CI runners often can't start Chrome's sandbox; it only loads the local preview.
            *(["--no-sandbox"] if os.environ.get("CI") else []),
            "about:blank",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        try:
            async with asyncio.timeout(TIMEOUT):
                endpoint = await self._devtools_endpoint()
            self._drain = asyncio.create_task(self._discard(self._process.stderr))
            self._session = aiohttp.ClientSession()
            self._socket = await self._session.ws_connect(endpoint, max_msg_size=0)
            self._reader = asyncio.create_task(self._read())
        except BaseException:
            await self._stop()
            raise
        return self

    async def __aexit__(self, *exc_info) -> None:
        with contextlib.suppress(Exception):
            async with asyncio.timeout(5):
                await self.send("Browser.close")
        await self._stop()

    async def _devtools_endpoint(self) -> str:
        while line := await self._process.stderr.readline():
            if match := re.search(rb"DevTools listening on (ws://\S+)", line):
                return match[1].decode()
        raise RuntimeError("The browser exited before DevTools started")

    @staticmethod
    async def _discard(stream: asyncio.StreamReader) -> None:
        while await stream.read(65536):
            pass

    async def _read(self) -> None:
        async for message in self._socket:
            if message.type is not aiohttp.WSMsgType.TEXT:
                continue
            data = json.loads(message.data)
            if "id" in data:
                future = self._pending.pop(data["id"], None)
                if future and not future.done():
                    if "error" in data:
                        future.set_exception(RuntimeError(data["error"].get("message")))
                    else:
                        future.set_result(data.get("result", {}))
                continue
            method, params = data.get("method"), data.get("params", {})
            if method == "Runtime.exceptionThrown":
                details = params["exceptionDetails"]
                self.errors.append(
                    details.get("exception", {}).get("description") or details["text"]
                )
            elif method == "Runtime.consoleAPICalled" and params.get("type") == "error":
                self.errors.append(
                    " ".join(
                        str(arg.get("value", arg.get("description", ""))) for arg in params["args"]
                    )
                )
            elif (
                method == "Log.entryAdded"
                and params["entry"].get("level") == "error"
                and not params["entry"].get("url", "").endswith("/favicon.ico")
            ):
                self.errors.append(
                    f"{params['entry'].get('text')} {params['entry'].get('url', '')}".strip()
                )
            for waiter in list(self._waiters):
                name, session_id, future = waiter
                if (
                    name == method
                    and session_id in (None, data.get("sessionId"))
                    and not future.done()
                ):
                    future.set_result(params)
                    self._waiters.remove(waiter)

    async def send(
        self, method: str, params: dict | None = None, session_id: str | None = None
    ) -> dict:
        self._next_id += 1
        message = {"id": self._next_id, "method": method, "params": params or {}}
        if session_id:
            message["sessionId"] = session_id
        future = asyncio.get_running_loop().create_future()
        self._pending[self._next_id] = future
        await self._socket.send_json(message)
        async with asyncio.timeout(TIMEOUT):
            return await future

    def wait_for(self, method: str, session_id: str | None = None) -> asyncio.Future:
        future = asyncio.get_running_loop().create_future()
        self._waiters.append((method, session_id, future))
        return future

    async def new_page(self, width: int, height: int, scale: float = 1) -> Page:
        target = await self.send("Target.createTarget", {"url": "about:blank"})
        attached = await self.send(
            "Target.attachToTarget", {"targetId": target["targetId"], "flatten": True}
        )
        page = Page(self, attached["sessionId"])
        for domain in ("Page", "Runtime", "Log"):
            await page.send(f"{domain}.enable")
        await page.send(
            "Emulation.setDeviceMetricsOverride",
            {"width": width, "height": height, "deviceScaleFactor": scale, "mobile": False},
        )
        return page

    async def _stop(self) -> None:
        for task in (getattr(self, "_reader", None), getattr(self, "_drain", None)):
            if task:
                task.cancel()
        if socket := getattr(self, "_socket", None):
            await socket.close()
        if session := getattr(self, "_session", None):
            await session.close()
        if self._process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self._process.pid, signal.SIGKILL)
            await self._process.wait()
        self._profile.cleanup()


class Page:
    """One browser tab."""

    def __init__(self, browser: Browser, session_id: str) -> None:
        self._browser = browser
        self._session_id = session_id

    async def send(self, method: str, params: dict | None = None) -> dict:
        return await self._browser.send(method, params, self._session_id)

    async def goto(self, url: str) -> None:
        loaded = self._browser.wait_for("Page.loadEventFired", self._session_id)
        await self.send("Page.navigate", {"url": url})
        async with asyncio.timeout(TIMEOUT):
            await loaded

    async def evaluate(self, expression: str):
        """Evaluate JavaScript, waiting for promises, and return the JSON value."""
        result = await self.send(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": True, "returnByValue": True},
        )
        if details := result.get("exceptionDetails"):
            raise RuntimeError(details.get("exception", {}).get("description") or details["text"])
        return result["result"].get("value")

    async def screenshot(self, selector: str | None = None) -> bytes:
        params: dict = {"format": "png", "captureBeyondViewport": True}
        if selector:
            box = await self.evaluate(
                f"(() => {{ const box = document.querySelector({json.dumps(selector)})"
                ".getBoundingClientRect(); return {x: box.x, y: box.y, width: box.width, "
                "height: box.height}; })()"
            )
            params["clip"] = {**box, "scale": 1}
        data = await self.send("Page.captureScreenshot", params)
        return base64.b64decode(data["data"])


async def run_tests(executable: str) -> tuple[list[dict], bytes | None]:
    """Run ui-tests.js and return the results, with a screenshot if any failed."""
    server = start_server()
    try:
        async with Browser(executable) as browser:
            page = await browser.new_page(1280, 1000)
            await page.goto(f"{server_url(server)}{PREVIEW}?mode=test")
            results = await page.evaluate("window.cardTestResults")
            results.append(
                {
                    "name": "no browser errors",
                    "ok": not browser.errors,
                    "error": " | ".join(browser.errors),
                }
            )
            failed = not all(result["ok"] for result in results)
            return results, (await page.screenshot() if failed else None)
    finally:
        server.shutdown()
        server.server_close()


async def take_screenshots(executable: str) -> dict[str, bytes]:
    """Render the README images: the healthy sample in both themes at 2x."""
    server = start_server()
    images = {}
    try:
        async with Browser(executable) as browser:
            for theme in ("light", "dark"):
                page = await browser.new_page(640, 1600, 2)
                await page.goto(
                    f"{server_url(server)}{PREVIEW}?mode=shot&scenario=healthy&theme={theme}"
                )
                await page.evaluate("window.cardPreviewReady")
                images[f"dashboard-card-{theme}.png"] = await page.screenshot("#stage")
            if browser.errors:
                raise RuntimeError("Browser errors: " + " | ".join(browser.errors))
    finally:
        server.shutdown()
        server.server_close()
    return images


def debug(port: int, open_browser: bool) -> None:
    server = start_server(port)
    url = f"{server_url(server)}{PREVIEW}"
    print(f"Card preview: {url}\nIt reloads when the card changes. Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    with contextlib.suppress(KeyboardInterrupt):
        threading.Event().wait()
    server.shutdown()
    server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("debug", help="open the interactive card preview")
    serve.add_argument("--port", type=int, default=8765, help="preview port (default 8765)")
    serve.add_argument("--no-open", action="store_true", help="don't open a browser window")
    tests = commands.add_parser("test", help="run the card UI tests headlessly")
    tests.add_argument("--json", action="store_true", help="print the results as JSON")
    shots = commands.add_parser("screenshots", help="regenerate the README card images")
    shots.add_argument("--output", type=Path, default=SCREENSHOTS, help="output directory")
    args = parser.parse_args()

    if args.command == "debug":
        debug(args.port, not args.no_open)
        return
    executable = find_browser()
    if executable is None:
        parser.exit(
            2,
            "No Chromium-based browser found. Install Chrome, Edge, Chromium, or Brave, or set CHROME_PATH.\n",
        )

    if args.command == "test":
        results, failure = asyncio.run(run_tests(executable))
        if failure:
            RESULTS.mkdir(exist_ok=True)
            (RESULTS / "card-ui-failure.png").write_bytes(failure)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for result in results:
                print(
                    f"{'PASS' if result['ok'] else 'FAIL'}  {result['name']}{'' if result['ok'] else f': {result["error"]}'}"
                )
            passed = sum(result["ok"] for result in results)
            print(f"{passed} passed, {len(results) - passed} failed")
            if failure:
                print(f"Screenshot of the failed run: {RESULTS / 'card-ui-failure.png'}")
        sys.exit(0 if failure is None else 1)

    images = asyncio.run(take_screenshots(executable))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in images.items():
        (args.output / name).write_bytes(data)
        print(args.output / name)


if __name__ == "__main__":
    main()
