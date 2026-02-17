#!/usr/bin/env python3
import atexit
import asyncio
import logging
import os
import tempfile
import threading
import time
from urllib.parse import urlparse

from flask import Flask, request, send_file
from pyppeteer import errors as pyppeteer_errors
from pyppeteer import launch

app = Flask(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
MAX_CONCURRENT_PAGES = int(os.environ.get("MAX_CONCURRENT_PAGES", "4"))
NAVIGATION_TIMEOUT_MS = int(os.environ.get("NAVIGATION_TIMEOUT_MS", "30000"))
logger = logging.getLogger(__name__)


def parse_positive_int(name, value, default):
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer")
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return parsed


def parse_non_negative_int(name, value, default):
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer")
    if parsed < 0:
        raise ValueError(f"{name} must be 0 or greater")
    return parsed


def parse_bool(value, default=False):
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be a valid http or https URL")


def resolve_chromium_path():
    configured_path = os.environ.get("CHROMIUM_EXECUTABLE_PATH")
    if configured_path:
        return configured_path
    for candidate in ["/usr/bin/chromium-browser", "/usr/bin/chromium"]:
        if os.path.exists(candidate):
            return candidate
    return None


class ScreenshotEngine:
    def __init__(self, max_concurrency, idle_timeout_seconds):
        self._max_concurrency = max_concurrency
        self._idle_timeout_seconds = idle_timeout_seconds
        self._ready = threading.Event()
        self._semaphore = threading.BoundedSemaphore(value=max_concurrency)
        self._state_lock = threading.Lock()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

        self._browser = None
        self._browser_lock = None
        self._active_requests = 0
        self._idle_timer = None
        self._last_used_at = time.monotonic()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    async def _ensure_browser(self):
        if self._browser is not None:
            return

        if self._browser_lock is None:
            self._browser_lock = asyncio.Lock()

        async with self._browser_lock:
            if self._browser is not None:
                return

            chromium_path = resolve_chromium_path()
            self._browser = await launch(
                executablePath=chromium_path,
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                ],
                handleSIGINT=False,
                handleSIGTERM=False,
                handleSIGHUP=False,
                autoClose=False,
            )
            logger.info("Browser instance started")

    async def _close_browser(self):
        if self._browser_lock is None:
            return

        async with self._browser_lock:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
                logger.info("Browser instance stopped after idle timeout")

    def _cancel_idle_timer_locked(self):
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

    def _schedule_idle_shutdown_locked(self):
        if self._idle_timeout_seconds <= 0:
            return

        self._cancel_idle_timer_locked()
        self._idle_timer = threading.Timer(self._idle_timeout_seconds, self._close_if_idle)
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def _close_if_idle(self):
        with self._state_lock:
            self._idle_timer = None
            if self._active_requests > 0:
                return
            idle_for = time.monotonic() - self._last_used_at
            if idle_for < self._idle_timeout_seconds:
                self._schedule_idle_shutdown_locked()
                return

        if self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self._close_browser(), self._loop).result(timeout=15)
            except Exception:
                logger.exception("Failed to stop browser after idle timeout")

    async def _capture(self, url, width, height, delay_ms, navigation_timeout_ms, user_agent, full_page):
        await self._ensure_browser()

        page = await self._browser.newPage()
        image_path = None
        try:
            await page.setViewport({"width": width, "height": height})
            await page.setUserAgent(user_agent)
            await page.goto(
                url,
                {
                    "timeout": navigation_timeout_ms,
                    "waitUntil": "domcontentloaded",
                },
            )
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

            with tempfile.NamedTemporaryFile(prefix="screenshot_", suffix=".png", delete=False) as handle:
                image_path = handle.name

            await page.screenshot({"path": image_path, "fullPage": full_page})
            return image_path
        finally:
            await page.close()

    def close(self):
        async def _shutdown():
            await self._close_browser()

        with self._state_lock:
            self._cancel_idle_timer_locked()

        if self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(_shutdown(), self._loop).result(timeout=10)
            except Exception:
                pass

            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=2)

    def capture(self, url, width, height, delay_ms, navigation_timeout_ms, user_agent, full_page):
        acquired = self._semaphore.acquire(timeout=30)
        if not acquired:
            raise RuntimeError("Server is busy. Please retry shortly.")

        with self._state_lock:
            self._active_requests += 1
            self._cancel_idle_timer_locked()

        try:
            result = asyncio.run_coroutine_threadsafe(
                self._capture(url, width, height, delay_ms, navigation_timeout_ms, user_agent, full_page),
                self._loop,
            ).result(timeout=60)
            with self._state_lock:
                self._last_used_at = time.monotonic()
            return result
        except TimeoutError as error:
            raise RuntimeError("Server is busy. Please retry shortly.") from error
        finally:
            with self._state_lock:
                self._active_requests = max(0, self._active_requests - 1)
                if self._active_requests == 0:
                    self._schedule_idle_shutdown_locked()
            self._semaphore.release()


screenshot_engine = ScreenshotEngine(
    max_concurrency=MAX_CONCURRENT_PAGES,
    idle_timeout_seconds=parse_non_negative_int(
        "BROWSER_IDLE_TIMEOUT_SECONDS",
        os.environ.get("BROWSER_IDLE_TIMEOUT_SECONDS"),
        300,
    ),
)
atexit.register(screenshot_engine.close)


@app.route('/screenshot')
def take_screenshot():
    url = request.args.get('url')
    if not url:
        return "URL parameter is required", 400

    try:
        validate_url(url)
        width = parse_positive_int("width", request.args.get('width'), 1280)
        full_page = parse_bool(request.args.get('full_page'), default=False)
        default_height = 900
        height = parse_positive_int("height", request.args.get('height'), default_height)
        delay_ms = parse_non_negative_int("delay_ms", request.args.get('delay_ms'), 1000)
        user_agent = request.args.get('user_agent', DEFAULT_USER_AGENT)
    except ValueError as error:
        return str(error), 400

    if full_page:
        height = default_height

    image_path = None
    try:
        image_path = screenshot_engine.capture(
            url=url,
            width=width,
            height=height,
            delay_ms=delay_ms,
            navigation_timeout_ms=NAVIGATION_TIMEOUT_MS,
            user_agent=user_agent,
            full_page=full_page,
        )

        response = send_file(image_path, mimetype='image/png')

        @response.call_on_close
        def cleanup_file():
            if image_path and os.path.exists(image_path):
                os.remove(image_path)

        return response
    except RuntimeError as error:
        return str(error), 503
    except pyppeteer_errors.TimeoutError:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return "Timed out while loading the page", 504
    except pyppeteer_errors.BrowserError as error:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return f"Failed to take screenshot: {error}", 500
    except Exception as error:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return f"Error: {error}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
