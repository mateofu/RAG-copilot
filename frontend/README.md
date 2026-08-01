# RAG Copilot frontend

Cliente React y TypeScript del copiloto documental. Consume la API mediante
`/api/v1`; Vite la redirige a `http://localhost:8000` durante el desarrollo.

## Desarrollo

```powershell
Copy-Item .env.example .env
npm ci
npm run dev
```

Abre `http://localhost:5173`. La API debe estar disponible en el puerto 8000.

## Calidad

```powershell
npm run format:check
npm run lint
npm run test
npm run test:e2e
npm run build
```

La sesión se conserva en `sessionStorage`; cerrar la pestaña elimina los tokens.
El cliente rota automáticamente el refresh token ante un `401` y evita ejecutar
más de una rotación concurrente.

Las respuestas HTTP se validan en runtime con Zod. Las páginas se cargan bajo
demanda, los fallos de render quedan contenidos por un Error Boundary y las
operaciones anuncian su resultado mediante una región accesible de notificaciones.
