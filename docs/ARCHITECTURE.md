# Arquitectura objetivo

## Objetivo

Ofrecer busqueda y conversacion sobre documentos empresariales sin filtrar datos
entre organizaciones, con respuestas trazables y una ingesta recuperable.

## Principios

1. El dominio no depende de FastAPI, SQLAlchemy, Celery ni del proveedor de IA.
2. Todo dato empresarial pertenece a una organizacion.
3. La autorizacion se valida en el caso de uso y se refuerza en persistencia.
4. Las operaciones asincronas son idempotentes, observables y reintentables.
5. Una respuesta RAG siempre conserva las fuentes que la sustentan.
6. Los proveedores externos se consumen mediante puertos propios.
7. Una funcionalidad termina con migraciones, pruebas y telemetria.

## Limites del sistema

- `identity`: usuarios, credenciales, sesiones y tokens.
- `organizations`: organizaciones, membresias, roles y limites.
- `documents`: metadatos, versiones, almacenamiento y ciclo de ingesta.
- `retrieval`: chunking, embeddings, indices, busqueda hibrida y reranking.
- `conversations`: conversaciones, mensajes, citas y consumo.
- `audit`: eventos de seguridad y acciones sensibles.

Cada modulo evolucionara con cuatro capas:

- `domain`: entidades, value objects, reglas y errores.
- `application`: casos de uso, comandos, consultas y puertos.
- `infrastructure`: SQLAlchemy, almacenamiento, colas y proveedores.
- `interfaces`: esquemas HTTP, dependencias y traduccion de errores.

No se crearan repositorios genericos ni abstracciones sin un caso de uso real.

## Estructura de paquetes

```text
backend/app/
|-- core/                         # Configuracion y preocupaciones transversales
|-- infrastructure/
|   |-- database/                 # Motor, sesiones y base SQLAlchemy compartidos
|   `-- task_queue/               # Configuracion del ejecutor asincrono
|-- interfaces/
|   `-- http/
|       `-- api_v1/               # Adaptador de entrada FastAPI
|-- modules/
|   |-- identity/
|   |   |-- domain/               # Reglas sin dependencias de frameworks
|   |   |-- application/          # Se agrega al existir el primer caso de uso
|   |   `-- infrastructure/
|   |       `-- persistence/      # Modelos y repositorios SQLAlchemy
|   `-- system/                   # Diagnosticos operativos
`-- main.py                       # Composition root de la API
```

Los modulos futuros (`identity`, `organizations`, `conversations`) siguen la
misma estructura, pero solo crean las capas que ya tengan una responsabilidad
real.

## Regla de dependencias

```text
interfaces --> application --> domain
                     ^
                     |
             infrastructure
```

- `domain` solo usa la biblioteca estandar y tipos propios.
- `application` puede importar `domain`, nunca FastAPI o SQLAlchemy.
- `infrastructure` implementa puertos declarados por `application`.
- `interfaces` invoca casos de uso; no consulta SQLAlchemy directamente.
- `main.py` y los entrypoints de workers ensamblan las implementaciones.
- Ningun modulo accede a tablas privadas de otro modulo; usa sus casos de uso o
  contratos publicos.

`core` no es un contenedor de utilidades arbitrarias. Solo alberga configuracion,
logging y politicas transversales que no pertenecen a un modulo.

## Multi-tenancy

La primera version usara base y esquema compartidos con `organization_id`.

- Todas las tablas con datos del cliente incluyen `organization_id`.
- Las claves unicas que representen datos del cliente incluyen el tenant.
- Ningun identificador de organizacion se acepta como autoridad desde el body.
- La organizacion activa proviene de la identidad autenticada.
- Los repositorios requieren el contexto de tenant en todas sus operaciones.
- Antes de produccion se agregara Row Level Security en PostgreSQL como defensa
  adicional; no reemplaza la autorizacion de aplicacion.

## Autorizacion

Roles iniciales:

- `owner`: administra organizacion, miembros, limites y documentos.
- `editor`: administra documentos y usa el copiloto.
- `viewer`: consulta documentos y conversaciones permitidas.

Los permisos se expresaran como capacidades (`documents:create`,
`documents:read`, etc.), evitando condicionales de rol dispersos.

## Ingesta documental

1. La API valida metadatos, tamano y tipo permitido.
2. El archivo se transmite al almacenamiento; no se carga completo en memoria.
3. Se calcula SHA-256 durante la escritura.
4. Una restriccion unica por organizacion, hash y version evita duplicados.
5. La transaccion crea el documento en `pending` y un evento de salida.
6. Un publicador envia el trabajo a la cola despues del commit.
7. El worker reclama la version, extrae, divide, genera embeddings e indexa.
8. Los estados y errores quedan persistidos; los reintentos no duplican chunks.

La entrega fiable del evento se implementara con un outbox transaccional, no con
una llamada directa a Celery dentro de la transaccion HTTP.

## Recuperacion

La primera version entrega busqueda vectorial con filtros obligatorios de tenant.
La segunda agrega busqueda textual, fusion de resultados y reranking. El contexto
enviado al modelo conserva documento, version, pagina y posicion del fragmento.

## Seguridad

- Contraseñas con un algoritmo adaptativo y secretos fuera del repositorio.
- Tokens de acceso cortos y refresh tokens rotatorios almacenados como hash.
- Limites de archivo, MIME verificado por contenido y nombres normalizados.
- Texto recuperado tratado como datos no confiables, nunca como instrucciones.
- Rate limiting por identidad y organizacion.
- Auditoria para autenticacion, miembros, documentos y cambios de permisos.
- Cotas de tokens, concurrencia y almacenamiento por organizacion.

## Observabilidad

Cada solicitud y tarea tendra `request_id` o `task_id`, `organization_id` cuando
aplique, duracion y resultado. Las metricas minimas cubren latencia HTTP, errores,
profundidad de cola, tiempo de ingesta, consumo de tokens y resultados de
recuperacion. Nunca se registran contraseñas, tokens ni contenido documental.

## Decisiones aplazadas

- Proveedor de modelos y dimensiones del embedding.
- Almacenamiento S3 compatible para produccion.
- Motor de extraccion y OCR.
- Proveedor de identidad externo frente a autenticacion propia.
- Umbrales y conjunto de evaluacion del RAG.

Estas decisiones se toman con requisitos o mediciones, no por preferencia de
framework.
