# OfferLens — every stage is a target. Ports/models come from .env + configs/models.yaml.
# SGLang runs from its own venv (Apple Silicon MLX build from source); see docs/DECISIONS.md.
SHELL := /bin/bash
-include .env
export

PY        ?= .venv/bin/python
SGLANG_PY ?= $(HOME)/code/sglang/.venv/bin/python
HOST      := 127.0.0.1
TEACHER_PORT ?= 30000
STUDENT_PORT ?= 30001
BASE_PORT    ?= 30002
APP_PORT     ?= 8000
cfg = $(shell $(PY) -c "from offerlens.settings import load_config as c; print(c('models')$(1))")
# Apple Silicon defaults: MLX backend; --mlx-enable-sampling is REQUIRED for json_schema masks there.
# On a Linux GPU: make serve-base SGLANG_ENV= SGLANG_EXTRA= SGLANG_PY=python
SGLANG_ENV   ?= SGLANG_USE_MLX=1
SGLANG_EXTRA ?= --disable-cuda-graph --mlx-enable-sampling
SGLANG = $(SGLANG_ENV) $(SGLANG_PY) -m sglang.launch_server --host $(HOST) $(SGLANG_EXTRA) \
         --max-running-requests 16

.PHONY: setup serve-teacher serve-base serve-student data train merge eval report app check fmt clean

setup:
	uv venv -p 3.12 .venv
	uv pip install -e ".[pipeline]" "curatorkit[hygiene]==0.1.22" --group dev
	$(PY) -m offerlens.schema
	$(PY) scripts/fetch_fonts.py

serve-teacher:
	$(SGLANG) --port $(TEACHER_PORT) --served-model-name teacher \
	  --model-path $(call cfg,['teacher']['repo']) --revision $(call cfg,['teacher']['revision']) \
	  --mem-fraction-static $(call cfg,['teacher']['mem_fraction'])

serve-base:
	$(SGLANG) --port $(BASE_PORT) --served-model-name base \
	  --model-path $(call cfg,['base']['repo']) --revision $(call cfg,['base']['revision']) \
	  --mem-fraction-static $(call cfg,['base']['mem_fraction'])

serve-student:
	$(SGLANG) --port $(STUDENT_PORT) --served-model-name student \
	  --model-path $(call cfg,['student']['path']) --mem-fraction-static $(call cfg,['student']['mem_fraction'])

data:
	$(PY) -m offerlens.schema
	$(PY) -m offerlens.data.generate
	$(PY) -m offerlens.data.curate

train:
	$(PY) -m offerlens.train.sft

merge:
	$(PY) -m offerlens.train.merge

eval:
	$(PY) -m offerlens.eval.run

report:
	$(PY) -m offerlens.eval.report

app:
	$(PY) -m uvicorn offerlens.api:app --host $(HOST) --port $(APP_PORT) --no-server-header

check:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests
	$(PY) -m mypy
	$(PY) -m pytest -q
	$(PY) -m bandit -r src -q
	$(PY) -m pip_audit --skip-editable --progress-spinner off -r <(uv pip compile -q pyproject.toml)
	gitleaks detect --no-banner

fmt:
	$(PY) -m ruff check --fix src tests
	$(PY) -m ruff format src tests

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache reports/runs
