FROM alpine:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Install required packages
RUN apk add --no-cache \
    chromium \
    python3 \
    py3-flask \
    py3-gunicorn \
    py3-pyppeteer

# Create working directory
WORKDIR /app

# Copy the application
COPY app.py .

# Expose the port
EXPOSE 5000

# Run the server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "60", "app:app"]
