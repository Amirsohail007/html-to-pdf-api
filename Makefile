SHELL := /bin/bash
PYTHON := python3
PIP := pip3
USER := $(shell whoami)

.PHONY: help install setup run clean docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo "  make help              - Show this help message"
	@echo "  make setup             - Full setup including dependencies"
	@echo "  make run-local         - Run the PDF API service (production-like)"
	@echo "  make clean             - Clean up temporary files and caches"
	@echo "  make docker-up         - Run the PDF API service in a docker container"
	@echo "  make docker-down       - Stop the docker container"
	@echo "  make docker-logs       - Show the logs of the docker container"

clean:
	@echo "Cleaning up..."
	find . -type d -name "venv" -print -exec rm -rf {} +
	find . -type d -name "__pycache__" -print -exec rm -rf {} +
	find . -type d -name "*.egg-info" -print -exec rm -rf {} +
	find . -type f -name "*.pyc" -print -delete
	find . -type f -name "*.pyo" -print -delete
	find . -type f -name "*.pyd" -print -delete

setup: clean
	$(PYTHON) -m venv venv
	./venv/bin/$(PIP) install --upgrade pip
	./venv/bin/$(PIP) install -r requirements.txt

# Run the PDF API service with hot-reload (development)
run-local:
	./venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1

# Run the PDF API service in a docker container	
docker-up:
	docker compose up -d --build

# Stop the docker container
docker-down:
	docker compose down

# Show the logs of the docker container
docker-logs:
	docker compose logs -f
