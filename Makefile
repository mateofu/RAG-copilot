.PHONY: install dev test lint typecheck migrate migration up down

install:
	cd backend && uv sync

dev:
	cd backend && uv run uvicorn app.main:app --reload

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check .

typecheck:
	cd backend && uv run mypy app

migrate:
	cd backend && uv run alembic upgrade head

migration:
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

up:
	cp -n backend/.env.example backend/.env || true
	docker compose up --build

down:
	docker compose down
