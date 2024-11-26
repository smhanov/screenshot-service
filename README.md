# Web Screenshot Service

A lightweight Docker-based web service that captures screenshots of web pages using headless Chromium.

## Features

- RESTful API for taking screenshots of web pages
- Customizable viewport dimensions
- Adjustable virtual time budget for page loading
- Configurable user agent string
- Automatic cleanup of screenshot files
- Concurrent request handling

## Prerequisites

- Docker
- Make (optional, for using provided Makefile commands)

## Quick Start

1. Build and run the service:
```bash
make all
```

Or manually with Docker:
```bash
docker build -t screenshot-service .
docker run -d -p 5000:5000 --name screenshot-service screenshot-service
```

## API Usage

### Take Screenshot

**Endpoint:** `GET /screenshot`

**Required Parameters:**
- `url`: The webpage URL to screenshot (URL encoded)

**Optional Parameters:**
- `width`: Viewport width in pixels (default: 1280)
- `height`: Viewport height in pixels (default: 900)
- `time_budget`: Time to wait for page load in milliseconds (default: 1000)
- `user_agent`: Custom User-Agent string

**Example Requests:**

Basic screenshot:
```bash
curl "http://localhost:5000/screenshot?url=https://example.com" --output screenshot.png
```

Custom viewport and timing:
```bash
curl "http://localhost:5000/screenshot?url=https://example.com&width=1920&height=1080&time_budget=2000" --output screenshot.png
```

## Management Commands

Build the service:
```bash
make build
```

Start the service:
```bash
make run
```

Stop the service:
```bash
make stop
```

Remove the container and image:
```bash
make clean
```

## Technical Details

- Built on Alpine Linux for minimal image size
- Uses Flask for the web server
- Implements headless Chromium for screenshot capture
- Handles concurrent requests safely with unique filenames
- Automatic cleanup of temporary screenshot files after serving

## Error Handling

The service returns:
- 400 Bad Request: When URL parameter is missing
- 500 Internal Server Error: For screenshot capture failures or other errors

## Security Notes

- Runs Chromium with --no-sandbox for containerized environment
- Implements automatic file cleanup to prevent disk space issues
- Uses system-level package management for dependencies

## License

[Your License Here]
