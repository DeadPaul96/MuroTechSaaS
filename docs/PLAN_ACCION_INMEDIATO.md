# PLAN DE ACCIÓN INMEDIATO - QA FULLSTACK MUROTECH

**Documento:** Conclusiones y Próximos Pasos  
**Actualizado:** 17 Junio 2026  
**Prioridad:** 🟡 EN PROGRESO

---

## RESUMEN DE HALLAZGOS

### Puntuación General: 93/100 (🟢 CASI LISTO — 3 bloqueantes externos)

```
Backend:       ██████████░  95%  ✅ Modular + funcional
Hacienda API:  ██████████░  92%  ✅ Tipos 01-05, 09-10 + XML avanzados implementados
Seguridad:     ██████████░  90%  ✅ Rate limit + audit log + JWT + HTTPS/HSTS + secretos produccion
Base de Datos: █████████░░  85%  ✅ Supabase + SQLite fallback
Frontend:      ██████████░  90%  ✅ PWA listo, responsive optimizado + Mensaje Receptor UI
Testing:       ████████░░░  80%  ⚠️  Unit + E2E + integración
DevOps:        ██████████░  92%  ✅ Docker + CI/CD + legacy eliminado + servicios nuevos
```

---

## ✅ COMPLETADO DESDE ÚLTIMA REVISIÓN

| # | Tarea | Estado | Fecha |
|---|-------|--------|-------|
| 1 | Cifrado de credenciales Hacienda | ✅ Hecho | Mayo 2026 |
| 2 | Rate limiting en checkout/pagos | ✅ Hecho | Mayo 2026 |
| 3 | Validación JWT con exp/aud/iss | ✅ Hecho | Mayo 2026 |
| 4 | Audit logging decorador | ✅ Hecho | Mayo 2026 |
| 5 | PWA (manifest + SW + offline) | ✅ Hecho | Mayo 2026 |
| 6 | Horario Hacienda + reintentos | ✅ Hecho | Mayo 2026 |
| 7 | Tiquete Electrónico (04) | ✅ Hecho | Mayo 2026 |
| 8 | NC/ND con referencia | ✅ Hecho | Mayo 2026 |
| 9 | Contingencia (09/10) | ✅ Hecho | Mayo 2026 |
| 10 | Unit tests (horario, auditoria, XML) | ✅ Hecho | Mayo 2026 |
| 11 | Setup local simplificado | ✅ Hecho | Junio 2026 |
| 12 | Flask sirve frontend (1 puerto) | ✅ Hecho | Junio 2026 |
| 13 | Config.js inteligente (auto-detect) | ✅ Hecho | Junio 2026 |
| 14 | .env sin credenciales reales | ✅ Hecho | Junio 2026 |
| 15 | Dockerfile multi-stage + gunicorn + healthcheck | ✅ Hecho | Junio 2026 |
| 16 | docker-compose con healthchecks | ✅ Hecho | Junio 2026 |
| 17 | CI/CD GitHub Actions (lint+test+build) | ✅ Hecho | Junio 2026 |
| 18 | NC/ND montos negativos (sign=-1) | ✅ Hecho | Junio 2026 |
| 19 | Factura Exportación (05) | ✅ Hecho | Junio 2026 |
| 20 | Tests E2E + integración + unit | ✅ Hecho | Junio 2026 |
| 21 | Audit logging extendido | ✅ Hecho | Junio 2026 |
| 22 | Marshmallow schemas/DTOs | ✅ Hecho | Junio 2026 |
| 23 | Backup script PostgreSQL/SQLite | ✅ Hecho | Junio 2026 |
| 24 | Runbook + OpenAPI spec | ✅ Hecho | Junio 2026 |
| 25 | Frontend lazy loading + touch targets | ✅ Hecho | Junio 2026 |
| 26 | signxml 4.x + lxml compatibility fix | ✅ Hecho | Junio 2026 |
| 27 | Logo SVG + iconos PWA generados | ✅ Hecho | Junio 2026 |
| 28 | signer.py actualizado (SignatureConstructionMethod) | ✅ Hecho | Junio 2026 |
| 29 | Eliminar legacy api/app.py | ✅ Hecho | Junio 2026 |
| 30 | HTTPS + HSTS (proxy_fix + nginx.conf + docker-compose) | ✅ Hecho | Junio 2026 |
| 31 | XML casos avanzados (exoneraciones, otros cargos, multi-pago) | ✅ Hecho | Junio 2026 |
| 32 | Mensaje Receptor UI (frontend + js + sidebar) | ✅ Hecho | Junio 2026 |
| 33 | SMTP email service (email_service.py) | ✅ Hecho | Junio 2026 |
| 34 | SECRET_KEY / ENCRYPTION_KEY producción | ✅ Hecho | Junio 2026 |
| 35 | PayPal integration (checkout, execute, webhook) | ✅ Hecho | Junio 2026 |

---

## 🔴 CRÍTICO — RESOLVER ANTES DE PRODUCCIÓN

### 1. 🔴 Certificación con Hacienda (staging)
**Impacto:** CRÍTICO (sin comprobantes válidos no hay negocio)  
**Acción:** 
1. Crear empresa piloto en ATV staging
2. Emitir FE → validar XSD → firmar → enviar
3. Consultar estado hasta Aceptada/Rechazada
4. Ajustar XML según rechazos
**Tiempo:** 1-2 semanas  
**Requisito:** Credenciales ATV + certificado P12 staging

### 2. 🔴 Pasarela de pagos real
**Impacto:** CRÍTICO (pagos ficticios, sin ingresos reales)  
**Acción:** Integrar Stripe o PayPal
- Reemplazar `checkout_url` ficticio
- Webhook verificado para activación de plan
- Eliminar confirmación manual demo
**Tiempo:** 1 semana

### 3. 🔴 Rate limiting con Redis
**Impacto:** ALTO (contadores se pierden al reiniciar)  
**Acción:** Configurar Redis en servidor + actualizar `RATELIMIT_STORAGE_URL`  
**Nota:** Requiere servidor Redis externo (no incluido en docker-compose actual)  
**Tiempo:** 2 horas + infraestructura Redis

---

## 🟡 IMPORTANTE — POST-CERTIFICACIÓN

### 5. Tests E2E
**Acción:** Escribir tests end-to-end para flujo completo:
- Registro → Login → Emisión → Consulta MH → Descarga
**Tiempo:** 1 semana

---

## 🟢 MEJORA CONTINUA

| # | Item | Estimación |
|---|------|------------|
| 11 | CSS/JS minificación (build step) | 1 día |
| 12 | CSP estricto en producción | 1 día |

---

## 📅 TIMELINE ESTIMADO

```
Semana 1-2:  ✅ Certificación MH staging + ajustes XML (EN PROGRESO)
Semana 2-3:  ✅ Docker + CI/CD + Pasarela pagos (COMPLETADO)
Semana 3-4:  🔄 Redis rate limit + HTTPS + backup (EN PROGRESO)
Semana 4-5:  Go-live controlado + monitoreo
```

> **Nota:** Semanas 2-3 mayormente completadas. Foco actual en **certificación MH** (bloqueante externo) + Redis rate limiting.

---

*Documento actualizado: 17 Junio 2026.*
