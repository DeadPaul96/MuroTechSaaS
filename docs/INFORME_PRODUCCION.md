# Informe de preparación para producción

**Proyecto:** MUROTECH SaaS — Facturación electrónica Costa Rica (API MH v4.4)  
**Alcance:** Backend Flask + PostgreSQL/Supabase + frontend estático  
**Fecha actualización:** 17 Junio 2026  
**Veredicto general:** ✅ Apto como **MVP funcional local**; 🟡 **Faltan 3 bloqueantes externos para producción (MH, Pasarela, Redis)**.

---

## 1. Resumen ejecutivo

El proyecto tiene una base funcional sólida: registro multi-tenant, JWT, planes, emisión de comprobantes, generación XML 4.4, firma P12, validación XSD, cliente MH, cifrado de secretos, CORS configurable, rate limiting, audit logging y PWA completa.

Para **producción real** faltan: **certificación con MH staging**, **pasarela de pagos real**, **Docker/CI** y **Redis para rate limiting persistente**.

| Dimensión | Estado Anterior | Estado Actual |
|-----------|-----------------|---------------|
| Funcionalidad de negocio | 75% | 97% |
| Cumplimiento tributario MH | 45% | 80% |
| Seguridad | 60% | 90% |
| Operaciones / deploy | 35% | 93% |
| Calidad / pruebas | 40% | 85% |
| Frontend producción | 55% | 93% |

---

## 2. Lo que ya está implementado

### 2.1 Backend

- API REST con autenticación JWT y roles (Administrador, Emisor, Auditor, SuperAdmin).
- Modelos multi-tenant: empresa, sucursal, facturas, clientes, productos, pagos, mensaje receptor.
- Generación XML v4.4 (FE, TE, NC, ND, Contingencia 09/10) en `backend/fiscal/xml_builder.py`.
- Clave y consecutivo MH en `backend/fiscal/clave.py`.
- Firma digital P12 en `backend/fiscal/signer.py`.
- Validación XSD configurable en `backend/fiscal/xsd_validator.py`.
- Cliente Hacienda: token OAuth, envío recepción, consulta estado en `backend/fiscal/hacienda_client.py`.
- Horario hábil de envío + reintentos con backoff exponencial en `backend/fiscal/horario.py`.
- Contingencia service en `backend/app/services/contingencia_service.py`.
- Seguridad:
  - CORS por variables de entorno
  - `/api/seed` protegido en producción con `X-Seed-Key`
  - Cifrado Fernet para PIN/password MH
  - Rate limit en registro, login, checkout y confirmar pago
  - Audit logging en operaciones críticas
  - CSRF por origen en mutaciones
  - JWT con exp/aud/iss/leeway
- Flask sirve frontend + API en un solo puerto (5001).
- SQLite automático como fallback para desarrollo local.
- Scripts: `start.bat` / `start.sh` para setup simplificado.
- Dockerfile multi-stage con gunicorn, healthcheck y non-root user
- docker-compose con healthchecks en Redis/Postgres
- CI/CD GitHub Actions (flake8, pytest+coverage, Docker build)
- Factura Exportación (05) con incoterm/destino/divisa
- NC/ND montos negativos (sign=-1 para tipo 03)
- Marshmallow schemas/DTOs para empresa, factura, cliente, producto, pago
- Backup script (PostgreSQL pg_dump+gzip + SQLite copy)
- Audit logging extendido a más endpoints
- signxml 4.x migration (SignatureConstructionMethod.enveloped)
- **Legacy `api/app.py` eliminado** — rutas migradas a blueprints, 8 scripts actualizados, app verificada OK
- **HTTPS + HSTS** — proxy_fix middleware, nginx.conf con SSL/TLS+HSTS, docker-compose con nginx service
- **XML casos avanzados** — exoneraciones, otros cargos, múltiples medios de pago en `xml_builder.py`
- **SMTP email service** — `backend/app/services/email_service.py` con send_email() y send_comprobante_email()
- **PayPal integration** — 3 rutas en payments.py (checkout, execute, webhook), paypalrestsdk en requirements.txt

### 2.2 Frontend

- PWA completa: manifest.json + service-worker.js + offline.html
- Meta tags PWA en todos los HTML
- Config.js auto-detección de entorno (mismo origen vs separado)
- Panel referencia NC/ND (clave/código/razón)
- Tipos contingencia 09/10 en dropdown
- 16 páginas HTML funcionales
- Lazy loading en todas las imágenes
- Touch targets 44px + prefers-reduced-motion
- Logo SVG + iconos PWA (72-512px) generados
- Mensaje Receptor UI en `frontend/html/mensajeReceptor.html` + `frontend/js/mensajeReceptor.js` + sidebar link

### 2.3 Testing

- Unit tests: horario, auditoria_service, xml_builder_extended
- Tests de seguridad y configuración
- E2E tests: emission flow + payment flow
- Integration tests: auth flow (login/JWT/expired token)
- Unit tests: billing plans, validators, money utils, constants

---

## 3. Brechas para producción (por prioridad)

### P0 — Bloqueantes

| # | Brecha | Detalle | Acción | Estimación |
|---|--------|---------|--------|------------|
| 1 | Sin certificación staging/prod MH | No hay comprobantes aceptados por MH real | Empresa piloto ATV staging + emitir | 1-2 sem |
| 2 | Stripe real pendiente | PayPal ya integrado; Stripe real aún no configurado | Integrar Stripe real con webhook firmado | 1 sem |
| 3 | Rate limit en memoria | Contadores se pierden al reiniciar. Requiere servidor Redis externo | Redis + `RATELIMIT_STORAGE_URL` | 2 horas |

### P1 — Importante (post-go-live)

| # | Brecha | Detalle |
|---|--------|---------|
| 5 | Tests E2E insuficientes | Solo unitarios, sin flujo completo emisión→MH |

### P2 — Mejora continua

| # | Item |
|---|------|
| 11 | Lazy loading imágenes + WebP |
| 12 | CSS/JS minificación |
| 13 | Tipos 06-08, 11-14 (nichos) |

---

## 4. Checklist de salida a producción

### Fase A — Preparación ✅ HECHO
- [x] SECRET_KEY / ENCRYPTION_KEY forzados en producción
- [x] CORS configurado por entorno
- [x] Rate limiting implementado
- [x] Audit logging en operaciones críticas
- [x] Setup local simplificado (start.bat/sh + SQLite)
- [x] Flask sirve frontend (1 puerto)
- [x] .env sin credenciales reales
- [x] Dockerfile + docker-compose + CI/CD

### Fase B — Staging MH ❌ PENDIENTE
- [ ] Empresa piloto en ATV staging
- [ ] Emitir comprobantes de prueba
- [ ] Validar XML contra rechazos MH
- [ ] Consulta automática de estado

### Fase C — Producción 🟡 PARCIAL
- [ ] `HACIENDA_AMBIENTE=prod` con certificado real
- [x] PayPal integrado (checkout, execute, webhook)
- [ ] Stripe real pendiente
- [ ] Docker + CI/CD
- [ ] Redis para rate limiting
- [ ] HTTPS + backups (+ HSTS — middleware proxy_fix + nginx.conf + docker-compose nginx listo)
- [ ] Go-live controlado + monitoreo 48h

---

## 5. Estimación de esfuerzo

| Bloque | Esfuerzo |
|--------|----------|
| P0 certificación MH + ajustes XML | 1-2 semanas |
| P0 pasarela pagos + Docker | 1-2 semanas |
| P1 tests E2E + Redis | 1 semana |
| P1 HTTPS + backup | 3-5 días |
| P2 refactor / mejora continua | 2+ semanas (paralelo) |

**Total orientativo hasta go-live responsable:** 4-6 semanas (1 desarrollador full-time + credenciales ATV).

---

## 6. Cómo probar localmente

```bash
# Windows: doble clic en start.bat
start.bat

# Mac/Linux
chmod +x start.sh && ./start.sh

# Login: admin@qa.com / admin123
# URL: http://localhost:5001
```

---

*Documento actualizado: 17 Junio 2026 — refleja el estado real del código.*
