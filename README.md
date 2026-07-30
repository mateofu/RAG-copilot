# RAG Copilot

Copiloto documental multiempresa basado en RAG. El proyecto esta en fase de
fundacion: la infraestructura minima existe, pero la ingesta y el motor RAG aun
no estan implementados.

## Capacidades actuales

- API FastAPI versionada en `/api/v1`.
- Configuracion tipada con `pydantic-settings`.
- SQLAlchemy asincrono preparado para PostgreSQL.
- Modelos preliminares de documentos y fragmentos.
- Configuracion base de Celery con Redis.
- PostgreSQL 17 con imagen de pgvector.
- Logs estructurados en JSON.
- Health check y prueba automatica inicial.
- Docker Compose para API, worker, PostgreSQL y Redis.

## Fuera del alcance actual

Todavia no existen autenticacion, organizaciones, RBAC, migraciones, carga de
PDF, tareas de ingesta, embeddings, recuperacion, conversaciones ni respuestas
RAG. Consulta [la arquitectura](docs/ARCHITECTURE.md) y
[el roadmap](docs/ROADMAP.md) antes de implementar un nuevo modulo.

## Ejecucion con Docker

```powershell
Copy-Item backend\.env.example backend\.env
docker compose up --build
```

API: `http://localhost:8000`

OpenAPI: `http://localhost:8000/docs`

Health check: `GET http://localhost:8000/api/v1/health`

Liveness: `GET http://localhost:8000/api/v1/health/live`

Readiness: `GET http://localhost:8000/api/v1/health/ready`

## Ejecucion local

Requiere Python 3.12 o superior, PostgreSQL, Redis y `uv`.

```powershell
Set-Location backend
Copy-Item .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

## Calidad

```powershell
Set-Location backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
```

## Migraciones

Con el stack de Docker activo:

```powershell
docker compose exec api uv run alembic upgrade head
```

Las migraciones no se ejecutan automaticamente al arrancar varios procesos. En
un despliegue se aplican una sola vez como una tarea previa a la nueva version.

No se debe presentar una capacidad como implementada hasta que tenga migracion,
pruebas y un flujo ejecutable.
