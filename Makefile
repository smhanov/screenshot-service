# Docker image name
IMAGE_NAME = screenshot-service

# Port mapping
PORT = 5000

.PHONY: build run stop clean

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

# Run the container
run:
	docker run -d -p $(PORT):$(PORT) --name $(IMAGE_NAME) $(IMAGE_NAME)

# Stop the container
stop:
	docker stop $(IMAGE_NAME)
	docker rm $(IMAGE_NAME)

# Clean up images
clean: stop
	docker rmi $(IMAGE_NAME)

# Build and run
all: build run
