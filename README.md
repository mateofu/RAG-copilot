# RAG Copilot

Copiloto documental multiempresa basado en RAG. El backend cubre identidad,
autenticacion, ingesta PDF, recuperacion vectorial y conversaciones RAG
persistentes de multiples turnos.

## Capacidades actuales

- API FastAPI versionada en `/api/v1`.
- Configuracion tipada con `pydantic-settings`.
- SQLAlchemy asincrono preparado para PostgreSQL.
- Esquema inicial de organizaciones, usuarios y membresias.
- Roles y permisos de dominio para aislamiento multiempresa.
- Registro inicial de organizaciones y propietarios.
- Autenticacion con access tokens JWT y refresh tokens rotatorios.
- Sesiones revocables y deteccion de reutilizacion de refresh tokens.
- Contexto organizacional validado contra membresias activas.
- Carga PDF segura por streaming con limite de tamano y SHA-256.
- Metadatos, versiones y deduplicacion aislados por organizacion.
- Outbox transaccional, publicador y worker Celery idempotente.
- Extraccion de texto por pagina y fragmentacion persistida.
- Embeddings semanticos locales con Ollama y `bge-m3`.
- Proveedor hash determinista como respaldo para desarrollo y pruebas.
- Busqueda vectorial trazable hasta documento, pagina y fragmento.
- Conversaciones RAG de multiples turnos con historial y citas persistidas.
- Interfaz web responsive para autenticacion, documentos, busqueda y chat.
- Configuracion base de Celery con Redis.
- PostgreSQL 17 con imagen de pgvector.
- Migraciones Alembic con extensiones `vector` y `citext`.
- Logs estructurados en JSON.
- Liveness y readiness para PostgreSQL y Redis.
- Docker Compose para API, worker, PostgreSQL y Redis.
- CI para formato, lint, tipos, pruebas, migraciones y build.

## Fuera del alcance actual

La busqueda hibrida, el reranking, las cuotas por organizacion y la operacion de
produccion pertenecen a hitos posteriores. Consulta
[la arquitectura](docs/ARCHITECTURE.md), [el roadmap](docs/ROADMAP.md) y las
reglas de [seguridad](docs/SECURITY.md) antes de ampliar el backend.

## Ejecucion con Docker

```powershell
Copy-Item backend\.env.example backend\.env
docker compose up --build
```

API: `http://localhost:8000`

OpenAPI: `http://localhost:8000/docs`

Health check: `GET http://localhost:8000/api/v1/health`

Frontend: `http://localhost:3000`

Liveness: `GET http://localhost:8000/api/v1/health/live`

Readiness: `GET http://localhost:8000/api/v1/health/ready`

Registro inicial de empresa: `POST http://localhost:8000/api/v1/organizations`

Autenticacion:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/context`, con `Authorization: Bearer <token>` y
  `X-Organization-Id: <uuid>`

Carga documental:

- `POST /api/v1/documents`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{documentNumber}`
- Encabezados: `Authorization: Bearer <token>` y
  `X-Organization-Id: <uuid>`.
- Cuerpo `multipart/form-data`: campo `title` y archivo `file`.
- Solo se aceptan PDFs de hasta 25 MB por defecto. El tipo declarado y la firma
  del contenido se validan antes de persistir sus metadatos.
- La respuesta inicial queda en estado `pending`; el scheduler publica el evento
  y el worker actualiza la version a `ready` o `failed`.

Busqueda vectorial:

- `GET /api/v1/documents/search/chunks?query=<texto>&limit=5`
- Requiere los mismos encabezados de autenticacion y organizacion.
- Ollama procesa los textos localmente con `bge-m3`; no requiere API key ni
  genera cargos por solicitud.

Reindexacion:

- `POST /api/v1/documents/reindex?limit=25`
- Por defecto solo encola versiones con chunks sin embedding.
- Usa `force=true` al cambiar de modelo o proveedor para regenerar todos los
  embeddings de la organizacion en lotes idempotentes.

El primer `docker compose up --build` descarga la imagen de Ollama y el modelo.
La descarga queda persistida en el volumen `ollama_data`. Para trabajar sin el
modelo temporalmente se puede usar:

```powershell
$env:RAG_COPILOT_EMBEDDING_PROVIDER="hashing"
docker compose up -d --build
```

El modo `hashing` solo es un respaldo funcional y no ofrece recuperacion
semantica de calidad.

Conversaciones RAG:

- `POST /api/v1/conversations`
- `POST /api/v1/conversations/{conversationId}/messages`
- `GET /api/v1/conversations?limit=20&offset=0`
- `GET /api/v1/conversations/{conversationId}`
- Cuerpo JSON: `{"question": "¿Qué dice el documento sobre vacaciones?"}`.
- La respuesta incluye citas persistidas con documento, pagina y fragmento.
- La continuacion utiliza el historial reciente, recupera contexto documental
  para la pregunta actual y conserva el aislamiento por organizacion.
- Por defecto se permiten 20 turnos por conversacion, se cargan los 10 mensajes
  mas recientes y el historial se limita a 8000 caracteres. Se configuran con
  `RAG_COPILOT_CONVERSATION_MAX_TURNS`,
  `RAG_COPILOT_CONVERSATION_HISTORY_MESSAGES` y
  `RAG_COPILOT_MAX_HISTORY_CHARACTERS`.
- Solo se persisten citas referenciadas por el modelo; marcadores ausentes o
  fuera de rango invalidan la respuesta completa.
- El chat usa localmente `qwen2.5:1.5b` mediante Ollama, sin cargos por uso.
- El contexto tiene presupuesto limitado y los fragmentos se tratan como datos
  no confiables para reducir el riesgo de prompt injection documental.
- Cada vector registra proveedor y modelo; la busqueda nunca mezcla indices de
  procedencias diferentes.

El registro publico se controla con
`RAG_COPILOT_PUBLIC_REGISTRATION_ENABLED`. Esta habilitado en el entorno local y
debe permanecer deshabilitado en produccion hasta disponer de rate limiting,
verificacion de correo y proteccion contra abuso.

## Ejecucion local

Requiere Python 3.12 o superior, PostgreSQL, Redis y `uv`.

```powershell
Set-Location backend
Copy-Item .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

En otra terminal:

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

Frontend local: `http://localhost:5173`

## Calidad

```powershell
Set-Location backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
```

```powershell
Set-Location frontend
npm run format:check
npm run lint
npm run test
npm run build
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
