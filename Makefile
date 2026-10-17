EXP ?= default

.PHONY: install db run test ingest eval

install:
	pip install -e ".[dev]"

db:
	docker compose up -d db

run:
	uvicorn trafikrag.api.main:app --reload

test:
	pytest

ingest:
	python -m trafikrag.ingestion.runner --config configs/$(EXP).yaml

eval:
	python -m trafikrag.evaluation.run_eval --config configs/experiments/$(EXP).yaml
