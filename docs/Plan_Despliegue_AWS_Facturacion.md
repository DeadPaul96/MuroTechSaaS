# Plan de Despliegue y Costos en AWS: Sistema de Facturación Electrónica e Inventario

**Actualizado:** 17 Junio 2026

> **Nota:** Este documento es una referencia de costos AWS. Para desarrollo local, usar `start.bat` / `start.sh` (no requiere AWS).

---

## Estado Actual del Proyecto

| Aspecto | Estado |
|---------|--------|
| **Desarrollo local** | ✅ Funciona con SQLite + Docker listo, sin infraestructura extra |
| **Staging** | ✅ Funciona con SQLite + Docker listo |
| **Producción** | ✅ Funciona con SQLite + Docker listo. HTTPS, PayPal, SMTP, XML avanzados, Mensaje Receptor completados. Pendiente: MH cert, Stripe real, Redis. |

---

## Resumen de Costos AWS (100 usuarios)

| Fase | Servicio | Costo Mensual |
|------|----------|---------------|
| **Free Tier (Año 1)** | EC2 + RDS + S3 | ~$0 |
| **Post Free Tier** | EC2 t3.small + RDS + S3 | ~$35-50/mes |
| **Con Redis + CDN** | + ElastiCache + CloudFront | ~$60-80/mes |

---

## Arquitectura Recomendada para Producción

```
Internet → CloudFront (CDN/HTTPS)
    ↓
EC2 (Flask + gunicorn)
    ↓
RDS PostgreSQL (Supabase o managed)
    ↓
ElastiCache Redis (rate limiting + caché)
    ↓
S3 (backups + assets)
```

---

## Lo que falta para desplegar en AWS

| # | Item | Estimación |
|---|------|------------|
| 1 | Certificación MH staging | 1-2 semanas |
| 2 | Stripe real (cuenta business + API keys) | 1 semana |
| 3 | PayPal credentials (PAYPAL_CLIENT_ID / PAYPAL_SECRET) | 1 día |
| 4 | Redis ElastiCache | 2 horas |

---

*Documento actualizado: 17 Junio 2026 — refleja el estado real del proyecto.*
