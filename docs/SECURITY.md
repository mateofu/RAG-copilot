# Seguridad

## Secretos

- `.env` nunca se versiona; `.env.example` solo documenta nombres y placeholders.
- Produccion obtiene secretos desde el gestor de secretos de la plataforma.
- `RAG_COPILOT_JWT_SECRET` debe ser aleatorio, tener al menos 32 caracteres y
  rotarse mediante un procedimiento controlado.
- Contraseñas, access tokens, refresh tokens y claves de proveedores no se
  incluyen en logs, errores, metricas ni respuestas de depuracion.
- Los refresh tokens se entregan una vez y solo su SHA-256 se persiste.
- Las contraseñas se almacenan exclusivamente como hashes Argon2.

Generar un secreto local en PowerShell:

```powershell
$bytes = New-Object byte[] 48
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToBase64String($bytes)
```

## Tokens

- Access token JWT de 15 minutos por defecto.
- Algoritmo permitido fijado en `HS256`; nunca se toma del token recibido.
- Validacion obligatoria de firma, expiracion, emisor, audiencia y claims.
- El access token solo identifica usuario y sesion. Roles y membresias se
  consultan para no conservar permisos obsoletos.
- Refresh token opaco, aleatorio, rotatorio y revocable.

## Reporte

No publiques vulnerabilidades como un issue publico. Hasta definir un canal
dedicado, comunicalas directamente al propietario del repositorio.
