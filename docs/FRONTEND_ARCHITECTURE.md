# Arquitectura del frontend

## Decisión

El frontend usa React, TypeScript, Vite, Tailwind CSS, Wouter, TanStack
Query, React Hook Form y Zod. Sigue Clean Architecture de forma pragmática y
organiza el código por funcionalidad.

Wouter cubre las rutas del SPA sin incorporar los modos SSR/RSC que generaban
advisories activos en React Router al crear este frontend.

```text
src/
|-- app/                 # composición, rutas y layout
|-- core/                # configuración, sesión y transporte HTTP
|-- features/
|   |-- auth/
|   |-- documents/
|   `-- conversations/
|       |-- domain/      # tipos y reglas sin React ni HTTP
|       |-- application/ # puertos de repositorio
|       |-- infrastructure/ # adaptadores HTTP
|       `-- presentation/   # páginas, componentes y hooks
`-- shared/              # piezas compartidas con uso real
```

## Reglas

- `domain` no importa React, fetch ni TanStack Query.
- `application` define los puertos que necesita la interfaz.
- `infrastructure` traduce el contrato HTTP a modelos internos.
- Los adaptadores validan cada respuesta HTTP con Zod antes de entregarla a la
  aplicación; una incompatibilidad se presenta como error controlado de gateway.
- `presentation` coordina interacción y caché, pero no construye solicitudes.
- El tenant procede de la membresía autenticada y se envía únicamente mediante
  `X-Organization-Id`.
- El estado remoto vive en TanStack Query; no se duplica en un store global.
- La sesión y la organización activa son los únicos estados globales.
- Los refresh tokens no se guardan en `localStorage`.

## Patrones aplicados

- Repository y Adapter para desacoplar la API.
- Dependency Injection mediante composición explícita.
- Provider para la sesión autenticada.
- Query Keys para separar caché por organización.
- Guard de rutas para impedir acceso anónimo.
- Single-flight para evitar rotaciones concurrentes del refresh token.
- Error Boundary para contener fallos de render no recuperables.
- Lazy loading por ruta para no cargar funcionalidades antes de necesitarlas.
- Modal accesible con foco contenido, cierre por Escape y restauración del foco.

No se crean casos de uso o factories para operaciones que solo delegan sin
añadir una regla. Las capas deben justificar su existencia con comportamiento
real y pruebas.
