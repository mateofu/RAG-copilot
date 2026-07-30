# Roadmap

Cada hito debe pasar Ruff, mypy y pytest, tener migraciones reversibles y
documentar cualquier nueva variable de entorno.

## Hito 0: base reproducible

- [x] Inicializar control de versiones.
- [x] Instalar `uv`, generar `uv.lock` y validar el build de Docker.
- [x] Agregar Alembic y una migracion que active `vector`.
- [x] Separar liveness de readiness para PostgreSQL y Redis.
- [x] Incorporar CI para formato, lint, tipos, pruebas y build.

Criterio de salida: un checkout limpio levanta el stack y aplica migraciones con
un unico procedimiento documentado.

## Hito 1: identidad y tenancy

- Organizaciones, usuarios, membresias y permisos.
- Registro controlado, login, refresh, logout y rotacion de tokens.
- Contexto de organizacion y autorizacion por capacidades.
- Restricciones compuestas y pruebas negativas de aislamiento.
- Eventos de auditoria.

Criterio de salida: dos organizaciones no pueden leer ni modificar datos entre
si, incluso usando identificadores validos de la otra.

## Hito 2: documentos e ingesta

- Interfaz de almacenamiento y adaptador local.
- Carga segura de PDF por streaming.
- Versiones, hash, deduplicacion y estados.
- Outbox transaccional y workers idempotentes.
- Extraccion, chunking estructural y metadatos de pagina.

Criterio de salida: reintentar cualquier paso no duplica documentos ni chunks y
los fallos pueden diagnosticarse y recuperarse.

## Hito 3: RAG trazable

- Abstracciones de embeddings y chat.
- Indice vectorial y filtros de tenant.
- Conversaciones, mensajes, citas y presupuesto de contexto.
- Limites y registro de consumo.
- Pruebas de integracion con proveedores simulados.

Criterio de salida: cada afirmacion recuperada enlaza a fragmentos persistidos y
ninguna consulta cruza organizaciones.

## Hito 4: calidad de recuperacion

- Busqueda textual y fusion hibrida.
- Reranking configurable.
- Dataset de evaluacion versionado.
- Metricas de retrieval y fidelidad.
- Defensa y pruebas contra prompt injection documental.

Criterio de salida: los cambios del pipeline se comparan contra una linea base y
no se despliegan si degradan los umbrales acordados.

## Hito 5: operacion

- Metricas, trazas, paneles y alertas.
- Cuotas por organizacion y control de costos.
- Almacenamiento de objetos y copias de seguridad.
- Pruebas end-to-end, carga y recuperacion ante desastres.
- Despliegue reproducible por ambientes.

Criterio de salida: existen objetivos de servicio, alertas accionables y un
procedimiento probado de restauracion.
