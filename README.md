# Web Screenshot Service

A lightweight Docker-based web service that captures screenshots using a shared headless Chromium instance.

## Features

- REST API for screenshot capture (`GET /screenshot`)
- Shared browser process (lower CPU/memory than per-request CLI launches)
- Concurrent request support with bounded parallelism
- Standard viewport screenshots and full-page screenshots
- Configurable wait budget and User-Agent
- Automatic cleanup of generated image files

## Prerequisites

- Docker
- Make (optional, for using provided Makefile commands)

## Quick Start

Build and run:

```bash
make all
```

Or manually:

```bash
docker build -t screenshot-service .
docker run -d -p 5000:5000 --name screenshot-service screenshot-service
```

## API

### Screenshot Endpoint

**Endpoint:** `GET /screenshot`

**Required query parameter:**

- `url`: HTTP/HTTPS URL to capture

**Optional query parameters:**

- `width`: viewport width in pixels (default: `1280`)
- `height`: viewport height in pixels (default: `900`)
- `full_page`: `true|false` (default: `false`)
- `delay_ms`: delay in milliseconds after page load and before screenshot (default: `1000`)
- `user_agent`: custom User-Agent string

### Full-page mode

When `full_page=true`, only `width` is needed.

- `height` is ignored in full-page mode
- output image includes the entire scrollable page height

## Examples

Basic screenshot:

```bash
curl "http://localhost:5000/screenshot?url=https://example.com" --output screenshot.png
```

Custom viewport screenshot:

```bash
curl "http://localhost:5000/screenshot?url=https://example.com&width=1920&height=1080&delay_ms=2000" --output screenshot.png
```

Full-page screenshot (width-only):

```bash
curl "http://localhost:5000/screenshot?url=https://example.com&width=1440&full_page=true&delay_ms=1500" --output screenshot-full.png
```

Delay behavior:

- The service waits for page load (`domcontentloaded`) first
- Then waits `delay_ms` milliseconds
- Then captures the screenshot

## Concurrency and Resource Usage

- The browser starts lazily on the first incoming screenshot request
- The service reuses one Chromium process and opens short-lived pages per request
- Parallel captures are bounded by `MAX_CONCURRENT_PAGES` (default: `4`)
- Requests beyond the limit wait briefly and then return `503` if the server is saturated
- Browser idle shutdown is controlled by `BROWSER_IDLE_TIMEOUT_SECONDS` (default: `300` = 5 minutes)
- After the idle timeout with no requests, Chromium is shut down to save memory and restarted automatically on the next request
- Gunicorn runs with one worker and threads to maximize browser reuse in low-resource environments

Set concurrency limit:

```bash
docker run -d -p 5000:5000 -e MAX_CONCURRENT_PAGES=6 --name screenshot-service screenshot-service
```

Set idle timeout (example: 60 seconds):

```bash
docker run -d -p 5000:5000 -e BROWSER_IDLE_TIMEOUT_SECONDS=60 --name screenshot-service screenshot-service
```

Disable idle shutdown (keep browser alive):

```bash
docker run -d -p 5000:5000 -e BROWSER_IDLE_TIMEOUT_SECONDS=0 --name screenshot-service screenshot-service
```

## Management Commands

```bash
make build   # Build the image
make run     # Run the container
make stop    # Stop and remove the container
make clean   # Remove container and image
```

## Error Handling

- `400 Bad Request`: invalid or missing query parameters
- `503 Service Unavailable`: server too busy
- `504 Gateway Timeout`: page load timeout
- `500 Internal Server Error`: browser/runtime capture failure

## Security Notes

- Chromium runs with `--no-sandbox` for container compatibility
- URL scheme is validated (`http`/`https` only)
- Screenshot files are deleted after each response is sent
