FROM alpine:latest

# Install required packages
RUN apk add --no-cache \
    chromium \
    python3 \
    py3-pip

# Install Python dependencies
RUN pip3 install --no-cache-dir flask

# Create working directory
WORKDIR /app

# Copy the application
COPY app.py .

# Expose the port
EXPOSE 5000

# Run the server
CMD ["python3", "app.py"]
