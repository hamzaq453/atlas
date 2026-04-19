.PHONY: install dev migrate migration test lint format check reset-db

install:
	poetry install
	poetry run pre-commit install

dev:
	poetry run uvicorn atlas.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	poetry run alembic upgrade head

migration:
	poetry run alembic revision --autogenerate -m "$(name)"

test:
	poetry run pytest -q

lint:
	poetry run ruff check src tests
	poetry run ruff format --check src tests
	poetry run mypy src tests

format:
	poetry run ruff check --fix src tests
	poetry run ruff format src tests

check: lint test

reset-db:
	poetry run python scripts/reset_db.py
