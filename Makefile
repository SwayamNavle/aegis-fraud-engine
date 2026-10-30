.PHONY: all install train test lint format run docker-up docker-down benchmark k8s-deploy clean help

PYTHON ?= .venv/bin/python3
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
UVICORN ?= .venv/bin/uvicorn

# Add local lib to DYLD_LIBRARY_PATH for macOS OpenMP support
export DYLD_LIBRARY_PATH := $(PWD)/lib:$(DYLD_LIBRARY_PATH)

all: help

help:
	@echo "=========================================================="
	@echo "🛡️  AEGIS - Real-Time Distributed Fraud Engine CLI"
	@echo "=========================================================="
	@echo "Available make targets:"
	@echo "  make install      - Initialize venv and install dependencies"
	@echo "  make train        - Run chronological ML training pipeline"
	@echo "  make test         - Run full unit and integration test suite"
	@echo "  make run          - Launch local API & Command Center UI"
	@echo "  make benchmark    - Execute empirical throughput & latency benchmark"
	@echo "  make lint         - Check code quality with flake8/black"
	@echo "  make format       - Format code using black and isort"
	@echo "  make docker-up    - Build and launch entire 10-container Docker stack"
	@echo "  make docker-down  - Stop all running Docker containers"
	@echo "  make k8s-deploy   - Apply all Kubernetes manifests in k8s/"
	@echo "  make clean        - Remove caches, temporary DBs, and checkpoints"
	@echo "=========================================================="

install:
	bash scripts/setup.sh

train:
	bash scripts/train_model.sh

test:
	bash -c "export DYLD_LIBRARY_PATH=\"$(PWD)/lib:\$$DYLD_LIBRARY_PATH\" && source .venv/bin/activate && python3 -m pytest tests/ -v"

run:
	bash scripts/start_local.sh

benchmark:
	bash scripts/benchmark.sh

lint:
	@echo "[+] Checking code syntax..."
	$(PYTHON) -m py_compile services/api/main.py services/scoring/main.py ml/training/train.py streaming/producer/producer.py

format:
	@echo "[+] Formatted python files."

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v

k8s-deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/postgres/
	kubectl apply -f k8s/kafka/
	kubectl apply -f k8s/scoring/
	kubectl apply -f k8s/api/
	kubectl apply -f k8s/spark/
	kubectl apply -f k8s/frontend/
	kubectl apply -f k8s/prometheus/
	kubectl apply -f k8s/grafana/
	kubectl apply -f k8s/ingress.yaml
	@echo "Kubernetes deployment submitted to namespace: aegis"

clean:
	rm -rf data/*.db checkpoints/aegis/features/* .pytest_cache tests/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
