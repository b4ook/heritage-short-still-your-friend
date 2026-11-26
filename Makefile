export RUN_ID := $(shell date -u +%Y%m%dT%H%M%S)-$(shell openssl rand -hex 3)
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: film smoke smoke-wan validate radio radio-draft costs prune test

film:
	@echo "RUN_ID=$(RUN_ID)"
	$(PY) -m pipeline.validate
	$(PY) -m pipeline.keyframes
	$(PY) -m pipeline.narration
	$(PY) -m pipeline.music
	$(PY) -m pipeline.shots
	$(PY) -m pipeline.assemble

smoke:
	@echo "RUN_ID=$(RUN_ID)"
	$(PY) -m pipeline.smoke

radio-draft:
	@echo "RUN_ID=$(RUN_ID)"
	$(PY) -m pipeline.validate
	$(PY) -m pipeline.assemble --radio --draft

smoke-wan:
	$(PY) -m pipeline.shots --smoke

validate:
	$(PY) -m pipeline.validate

radio:
	@echo "RUN_ID=$(RUN_ID)"
	$(PY) -m pipeline.validate
	$(PY) -m pipeline.narration
	$(PY) -m pipeline.assemble --radio

costs:
	$(PY) -m pipeline.costs

prune:
	$(PY) -m pipeline.prune

test:
	$(PY) -m pytest tests
