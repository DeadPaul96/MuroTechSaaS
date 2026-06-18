# Runbook Operacional — MUROTECH SaaS

**Última actualización:** 17 Junio 2026
**Alcance:** Procedimientos operacionales para mantenimiento, incidentes y despliegue.

---

## 1. Rotación de Llave Criptográfica (P12)

La llave criptográfica `.p12` del Ministerio de Hacienda debe renovarse cada 2 años.

### Pasos:
1. Ingresar a ATV/OVi con credenciales del contribuyente.
2. **Comprobantes Electrónicos → Llave Criptográfica** (producción o pruebas según corresponda).
3. Crear nuevo PIN de 4 dígitos y descargar el nuevo `.p12`.
4. En MUROTECH: **Configuración → Facturación → Subir nueva llave P12**.
5. Verificar emisión de prueba en staging antes de producción.

### Verificación:
- Emitir una factura de prueba en ambiente staging.
- Consultar estado en MH: debe ser `Aceptada`.
- Si hay rechazo, verificar PIN y vigencia del certificado.

---

## 2. Migración Staging → Producción

### Pre-requisitos:
- [ ] Certificación exitosa en ATV Staging (mínimo 10 comprobantes aceptados).
- [ ] Llave criptográfica de producción descargada.
- [ ] Usuario y contraseña de producción generados en ATV.
- [ ] `SECRET_KEY` y `ENCRYPTION_KEY` configurados en servidor.

### Pasos:
1. Actualizar variables de entorno en producción:
   ```env
   HACIENDA_AMBIENTE=prod
   HACIENDA_SEND_ENABLED=true
   RATELIMIT_STORAGE_URL=redis://redis:6379/0
   FLASK_ENV=production
   ```
2. Subir llave `.p12` de producción en Configuración → Facturación.
3. Actualizar `api_usuario` y `api_password` con credenciales de producción.
4. Emitir 1 factura de prueba y verificar aceptación de MH.
5. Monitorear logs durante 48 horas.

### Rollback:
- Cambiar `HACIENDA_AMBIENTE=stag` y reiniciar.
- Los comprobantes emitidos en prod no se pueden revertir.

---

## 3. Manejo de Incidentes MH (Hacienda)

### Error: Token MH rechazado (401/403)
- **Causa:** Credenciales ATV incorrectas o expiradas.
- **Acción:** Verificar `api_usuario` y `api_password` en Configuración → Facturación. Regenerar contraseña en ATV si es necesario.

### Error: Recepción MH rechazada (400)
- **Causa:** XML no cumple XSD v4.4 o datos inválidos.
- **Acción:** Revisar `respuesta_hacienda` en la factura. Ajustar `xml_builder.py` según el error específico.

### Error: 429 Too Many Requests
- **Causa:** Rate limit de MH excedido.
- **Acción:** El sistema ya tiene reintentos con backoff exponencial. Si persiste, reducir concurrencia de envío.

### Error: 503 Service Unavailable
- **Causa:** MH temporalmente fuera de servicio.
- **Acción:** Los comprobantes quedan en estado `Pendiente`. El sistema reintentará automáticamente. Verificar [estado de MH](https://www.hacienda.go.cr/).

### Comprobantes en contingencia (09/10)
- Usar cuando no haya internet o MH esté caído.
- El sistema marca `situacion=2` automáticamente.
- Sincronizar cuando se recupere el servicio: `POST /api/contingencia/sincronizar`.

---

## 4. Backup y Restauración

### Backup automático:
Script de backup disponible: `backend/scripts/backup_db.py` — soporta PostgreSQL (pg_dump+gzip) y SQLite (copia directa). Configurar con `--retention-days 30`.

```bash
# Cron job (ejecutar a las 2am diario)
0 2 * * * cd /app && python scripts/backup_db.py --retention-days 30
```

### Restauración manual:
```bash
# PostgreSQL
gunzip -c murotech_backup_YYYYMMDD.sql.gz | psql $DATABASE_URL

# SQLite (detener servidor primero)
cp murotech_backup_YYYYMMDD.db murotech_saas.db
```

---

## 5. Monitoreo y Health Checks

### Endpoint de salud:
```
GET /api/v1/config
```
Retorna estado del sistema, planes y tipos de documento soportados.

### Health check de Docker:
```bash
docker inspect --format='{{.State.Health.Status}}' murotech-web
```

### Sentry:
- Configurar `SENTRY_DSN` en producción.
- Tasa de muestreo: 10% (`traces_sample_rate=0.1`).

---

## 6. Despliegue de Emergencia

### Hotfix rápido:
```bash
# 1. Pull de cambios
git pull origin main

# 2. Rebuild Docker
cd backend/docker
docker-compose down && docker-compose up -d --build

# 3. Migrar BD si es necesario
docker-compose exec web flask db upgrade

# 4. Verificar
curl http://localhost:5001/api/v1/config
```

### Rollback de versión:
```bash
# Revertir al commit anterior
git revert HEAD --no-edit
docker-compose up -d --build
```

### CI/CD Automático:
GitHub Actions está configurado en `.github/workflows/backend-ci.yml` — ejecuta lint (flake8), tests (pytest + coverage) y build Docker automáticamente en cada push a `main`.

---

## 7. Rotación de Secretos

### SECRET_KEY:
1. Generar nueva: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Actualizar `.env` en producción.
3. Todos los tokens JWT existentes quedan invalidados (usuarios deben re-login).

### ENCRYPTION_KEY:
1. Generar nueva: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. **Antes de cambiarla**, descifrar todas las credenciales cifradas.
3. Actualizar `.env`, recifrar credenciales, reiniciar.

### signxml v4.x:
La firma XML usa signxml>=4.4.0 con `SignatureConstructionMethod.enveloped` (no el string `'enveloped'` de v2.x). Si se revierte a signxml 2.x, actualizar `fiscal/signer.py` de vuelta al string method.

---

## 8. Email y Comprobantes

### Envío de comprobantes:
El servicio `backend/app/services/email_service.py` permite enviar comprobantes XML por email al cliente.

Configurar en .env:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
SMTP_FROM=noreply@murotech.com
```

### PayPal:
PayPal integration disponible en `/api/pagos/paypal/checkout`. Configurar:
```
PAYPAL_MODE=sandbox  # o live
PAYPAL_CLIENT_ID=tu_client_id
PAYPAL_CLIENT_SECRET=tu_client_secret
```
