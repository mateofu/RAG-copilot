# Instalacion

## Requisitos

- Docker Desktop con Docker Compose, o Python 3.12+ con `uv`.
- Puertos locales `8000`, `5432` y `6379` disponibles.

## Opcion recomendada: Docker

```powershell
Copy-Item backend\.env.example backend\.env
docker compose up --build
```

Verificacion:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

## Opcion local

Las URLs de `.env.example` usan los nombres de servicio de Docker. Para ejecutar
la API fuera de Docker, cambia los hosts `postgres` y `redis` por `localhost`.

```powershell
Set-Location backend
Copy-Item .env.example .env
uv sync
uv run pytest
uv run uvicorn app.main:app --reload
```

El repositorio aun no contiene `uv.lock`. Hasta generarlo y versionarlo, las
versiones instaladas pueden variar dentro de los rangos de `pyproject.toml`.
