# Plan de Mejoras para MUROTECH

**Actualizado:** 17 Junio 2026  
**Estado:** 🟢 Progreso significativo

---

## Resumen de Progreso

| Área | Antes (Mayo) | Ahora (Junio) | Cambio |
|------|-------------|---------------|--------|
| Seguridad | 60% | 90% | +30% |
| Hacienda API | 70% | 92% | +22% |
| Frontend | 55% | 90% | +35% |
| DevOps | 40% | 93% | +53% |
| Testing | 45% | 85% | +40% |

---

## 1. Seguridad y Hardening

### 1.1 Validación de secretos en producción ✅ HECHO
- ✅ `SECRET_KEY` forzado en producción
- ✅ `ENCRYPTION_KEY` obligatorio en producción
- ✅ `ProductionConfig.validate()` impide arranque sin secretos

### 1.2 Rate limiting persistente 🟡 PARCIAL
- ✅ Rate limiting en checkout (10/h) y confirmar pago (10/h)
- ✅ Rate limiting en registro (10/h) y login (20/h)
- ❌ **FALTA:** Migrar a Redis para persistencia entre reinicios (requiere servidor Redis externo)
- **Acción:** Configurar `RATELIMIT_STORAGE_URL=redis://...` en servidor

### 1.3 JWT seguro ✅ HECHO
- ✅ Validación de `aud`, `iss`, `exp`, `iat`
- ✅ Expiración configurable via `JWT_EXPIRY`
- ✅ Lógica de leeway para clock drift

### 1.4 Protección CSRF y CORS ✅ HECHO
- ✅ Validación de origen en mutaciones (middleware)
- ✅ `CORS_ORIGINS` explícito en producción (sin `*`)
- ✅ CSRF token via `X-CSRF-Token` header

### 1.5 Auditoría de acciones críticas ✅ HECHO
- ✅ `@audit_log` decorador implementado
- ✅ Auditoría en: logout, config_empresa, suspender_plan, reactivar_plan, confirmar_pago
- ✅ Ampliado a CRUD usuarios y facturación con @audit_log

### 1.6 Cifrado de credenciales ✅ HECHO
- ✅ `encrypt_text` / `decrypt_text` con Fernet
- ✅ P12 cifrado en base de datos
- ✅ API password y PIN cifrados

---

## 2. Integración Hacienda API 4.4

### 2.1 Tipos de documentos ✅ PARCIAL
- ✅ Factura Electrónica (01)
- ✅ Nota de Débito (02) con referencia
- ✅ Nota de Crédito (03) con referencia
- ✅ Tiquete Electrónico (04)
- ✅ Factura de Exportación (05) — Implementado (incoterm/destino/divisa)
- ❌ Tipos 06-08, 11-14 — FALTA (nichos específicos)
- ✅ Contingencia Factura (09)
- ✅ Contingencia Tiquete (10)
- NC/ND montos negativos: ✅ sign=-1 para tipo 03

### 2.2 Horario y reintentos ✅ HECHO
- ✅ `validar_horario_envio()` — 8am-8pm Lun-Sáb, sin domingos/feriados
- ✅ `enviar_con_reintentos()` — backoff exponencial (2s→4s→8s), máx 3 reintentos
- ✅ Feriados CRC 2026 incluidos
- ✅ No reintenta en errores 4xx (excepto 408/429)

### 2.3 Contingencia ✅ HECHO
- ✅ Tipos 09/10 con `situacion=2` en clave
- ✅ Servicio `contingencia_service.py` para marcar y sincronizar
- ✅ Endpoints: `POST /api/facturas/contingencia/<id>` y `POST /api/facturas/contingencia/sincronizar`

### 2.4 Certificación con MH ❌ FALTA
- ❌ **BLOQUEANTE:** No hay comprobantes aceptados por MH real
- **Acción:** Crear empresa piloto en ATV staging y emitir
- **Estimación:** 1-2 semanas
- ⚠️ signxml actualizado a v4.4+ con SignatureConstructionMethod.enveloped

---

## 3. Frontend

### 3.1 PWA ✅ HECHO
- ✅ `manifest.json` con iconos y shortcuts
- ✅ `service-worker.js` con cache-first (estático) y network-first (API)
- ✅ `offline.html` como fallback
- ✅ Meta tags PWA en todos los HTML

### 3.2 Configuración por entorno ✅ HECHO
- ✅ `config.js` detecta automáticamente localhost vs producción
- ✅ Usa rutas relativas `/api/...` cuando Flask sirve frontend
- ✅ Elimina problemas de CORS en desarrollo local

### 3.3 Setup simplificado ✅ HECHO
- ✅ `start.bat` (Windows) y `start.sh` (Mac/Linux)
- ✅ Flask sirve frontend + API en un solo puerto (5001)
- ✅ SQLite automático si no hay Supabase configurado
- ✅ Datos de prueba con `/api/seed`

### 3.4 Responsive 🟡 EN REVISIÓN
- ✅ Viewport meta en todos los HTML
- ⚠️ Algunas pantallas necesitan ajustes mobile
- ✅ loading="lazy" en todos los img
- ✅ Touch targets 44px + prefers-reduced-motion
- ✅ Logo SVG + iconos PWA (72-512px) generados
- ❌ **FALTA:** WebP optimization
- ❌ **FALTA:** CSS/JS minificación

### 3.5 NC/ND Panel de referencia ✅ HECHO
- ✅ Panel visible solo para tipos 02/03
- ✅ Campos: clave referencia, código razón, razón
- ✅ Validación backend `referencia_id` obligatorio para NC/ND

### 3.6 Mensaje Receptor UI ✅ HECHO
- ✅ Interfaz en `frontend/html/mensajeReceptor.html`
- ✅ Lógica en `frontend/js/mensajeReceptor.js`
- ✅ Enlace en sidebar de navegación
- ✅ Permite consultar y visualizar mensajes de Hacienda

---

## 4. Base de Datos y DevOps

### 4.1 Multi-DB ✅ HECHO
- ✅ Supabase PostgreSQL en producción
- ✅ SQLite automático en desarrollo local (fallback)
- ✅ `config.py` resuelve URI desde variables de entorno

### 4.2 Migraciones 🟡 PARCIAL
- ✅ Flask-Migrate configurado
- ⚠️ Scripts manuales para migraciones complejas
- ❌ **FALTA:** Alembic versionado completo

### 4.3 Infraestructura ✅ EN PROGRESO
- ✅ Dockerfile + docker-compose — Completado
- ✅ CI/CD pipeline completo — Completado (GitHub Actions)
- ✅ HTTPS + SSL en servidor — Completado (proxy_fix middleware + nginx.conf con SSL/TLS+HSTS + docker-compose nginx service)
- ✅ Backup automático de DB — Completado (scripts/backup_db.py)
- ✅ Legacy api/app.py eliminado — Rutas migradas a blueprints, 8 scripts actualizados
- ❌ **FALTA:** Redis para rate limiting persistente (requiere servidor externo)

---

## 5. Testing

### 5.1 Unit tests ✅ EN EXPANSIÓN
- ✅ `test_horario.py` — validación horario y reintentos
- ✅ `test_auditoria_service.py` — sanitización y log_change
- ✅ `test_xml_builder_extended.py` — XML tipos 01, 02, 03, 04, 09, 10
- ✅ E2E tests: test_emission_flow, test_payment_flow
- ✅ Integration tests: test_auth_flow
- ✅ Unit tests: billing plans, validators, money utils, constants
- ✅ Marshmallow schemas/DTOs
- ✅ XML exoneraciones, otros cargos, múltiples medios de pago — Implementados en xml_builder.py
- ❌ **FALTA:** Tests para contingencia_service, empresa_service, payments blueprint
- ❌ **FALTA:** Tests de integración con MH

---

## 6. Pagos y Planes

### 6.1 Planes ✅ HECHO
- ✅ 4 planes de suscripción
- ✅ Modelo de suscripciones
- ✅ Historial de pagos

### 6.2 Pasarela 🟡 PARCIAL
- ✅ PayPal integrado (3 rutas: checkout, execute, webhook)
- ✅ SMTP para envío de comprobantes — email_service.py con send_email() + send_comprobante_email()
- ❌ **FALTA:** Stripe real + webhook firmado
- **Estimación:** 1 semana (Stripe)

---

*Documento actualizado: 17 Junio 2026 — refleja el estado real del código.*
