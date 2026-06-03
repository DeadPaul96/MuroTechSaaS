# PLAN DE ACCIÓN INMEDIATO - QA FULLSTACK MUROTECH

**Documento:** Conclusiones y Próximos Pasos  
**Actualizado:** 2 Junio 2026  
**Prioridad:** 🟡 EN PROGRESO

---

## RESUMEN DE HALLAZGOS

### Puntuación General: 78/100 (🟡 CASI LISTO PARA PRODUCCIÓN)

```
Backend:       █████████░  90%  ✅ Modular + funcional
Hacienda API:  █████████░  85%  ✅ Tipos 01-04, 09-10 implementados
Seguridad:     ████████░░  78%  ✅ Rate limit + audit log + JWT mejorado
Base de Datos: ████████░░  80%  ✅ Supabase + SQLite fallback
Frontend:      ███████░░░  70%  ⚠️  PWA listo, responsive en revisión
Testing:       ██████░░░░  65%  ⚠️  Unit tests básicos
DevOps:        ██████░░░░  60%  ⚠️  Scripts de inicio, falta Docker
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

### 3. 🔴 Docker + CI/CD
**Impacto:** CRÍTICO (no hay contenedor ni deploy automático)  
**Acción:** 
1. Crear Dockerfile
2. GitHub Actions con test + deploy
3. docker-compose para desarrollo local
**Tiempo:** 3-5 días

### 4. 🔴 Rate limiting con Redis
**Impacto:** ALTO (contadores se pierden al reiniciar)  
**Acción:** Configurar Redis en servidor + actualizar `RATELIMIT_STORAGE_URL`  
**Tiempo:** 2 horas + infraestructura Redis

---

## 🟡 IMPORTANTE — POST-CERTIFICACIÓN

### 5. Tests E2E
**Acción:** Escribir tests end-to-end para flujo completo:
- Registro → Login → Emisión → Consulta MH → Descarga
**Tiempo:** 1 semana

### 6. Factura de Exportación (05)
**Acción:** Implementar tipo 05 con campos adicionales (incoterm, destino, etc.)  
**Tiempo:** 3-5 días  
**Nota:** Solo necesario si hay clientes exportadores

### 7. NC/ND con montos negativos
**Acción:** Ajustar signo en totales para devoluciones completas  
**Tiempo:** 2-3 días

### 8. Backup automático
**Acción:** Cron job para dumps de Supabase + retención  
**Tiempo:** 2 horas

### 9. HTTPS + HSTS
**Acción:** Certificados SSL + headers de seguridad estrictos  
**Tiempo:** 2 horas + configuración de dominio

---

## 🟢 MEJORA CONTINUA

| # | Item | Estimación |
|---|------|------------|
| 10 | Lazy loading imágenes + WebP | 2 días |
| 11 | CSS/JS minificación (build step) | 1 día |
| 12 | Más unit tests (empresa, factura, blueprints) | 3-5 días |
| 13 | Runbook operacional | 2 días |
| 14 | CSP estricto en producción | 1 día |
| 15 | Mensaje Receptor UI | 3 días |

---

## 📅 TIMELINE ESTIMADO

```
Semana 1-2:  Certificación MH staging + ajustes XML
Semana 2-3:  Pasarela pagos real + Docker
Semana 3-4:  Tests E2E + Redis rate limit
Semana 4-5:  HTTPS + backup + mejoras frontend
Semana 5-6:  Go-live controlado + monitoreo
```

---

*Documento actualizado: 2 Junio 2026.*
