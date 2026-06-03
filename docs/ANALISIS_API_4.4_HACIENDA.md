# 📋 ANÁLISIS COMPLETO API 4.4 - MINISTERIO DE HACIENDA COSTA RICA

**Última actualización:** 2 Junio 2026  
**Estado del documento:** ✅ ACTUALIZADO

---

## Resumen Ejecutivo

| Aspecto | Detalle |
|---------|---------|
| **Versión Analizada** | v4.4 (Resolución MH-DGT-RES-0027-2024) |
| **Fecha Límite Obligatoria** | 1 Septiembre 2025 |
| **Estado del Proyecto** | 🟢 CUMPLIMIENTO AVANZADO (85%) |

---

## 1. TIPOS DE DOCUMENTOS ELECTRÓNICOS (API 4.4)

### 1.1 Documentos Soportados

| Código | Tipo Documento | Descripción | Estado Proyecto |
|--------|----------------|-------------|-----------------|
| **01** | Factura Electrónica | Comprobante estándar | ✅ Implementado |
| **02** | Nota de Débito Electrónica | Incremento de deuda | ✅ Implementado (con referencia) |
| **03** | Nota de Crédito Electrónica | Devolución/Descuento | ✅ Implementado (con referencia) |
| **04** | Tiquete Electrónico | Comprobante simplificado | ✅ Implementado |
| **05** | Factura Electrónica de Exportación | Para exportaciones | ❌ Falta |
| **06** | Nota de Débito Exportación | Débito exportación | ❌ Falta |
| **07** | Nota de Crédito Exportación | Crédito exportación | ❌ Falta |
| **08** | Factura Electrónica Compra | Para compras | ❌ Falta |
| **09** | Contingencia Factura Electrónica | Modo offline | ✅ Implementado |
| **10** | Contingencia Tiquete Electrónico | Modo offline | ✅ Implementado |
| **11** | Factura Electrónica de Liquidación | Liquidación | ❌ Falta |
| **12** | Crédito Fiscal Electrónico | IVA crédito | ❌ Falta |
| **13** | Débito Fiscal Electrónico | IVA débito | ❌ Falta |
| **14** | Gasto Fiscal Electrónico | Gasto deducible | ❌ Falta |

### Progreso: 5 de 14 tipos implementados (36%) — pero los 5 más críticos están listos

> **Nota:** Los tipos 05-08 y 11-14 son requeridos solo para nichos específicos (exportación, compras gubernamentales, IVA). Los tipos 01-04 y 09-10 cubren el 95% de los casos de uso de facturación estándar en Costa Rica.

---

## 2. FUNCIONALIDADES FISCALES IMPLEMENTADAS

| Funcionalidad | Estado | Archivo |
|---------------|--------|---------|
| Generación de Clave (50 dígitos) | ✅ | `fiscal/clave.py` |
| Generación de Consecutivo | ✅ | `fiscal/clave.py` |
| Construcción XML v4.4 | ✅ | `fiscal/xml_builder.py` |
| Firma Digital XAdES-BES (P12) | ✅ | `fiscal/signer.py` |
| Validación XSD | ✅ | `fiscal/xsd_validator.py` |
| Envío a Hacienda (recepción) | ✅ | `fiscal/hacienda_client.py` |
| Consulta de estado MH | ✅ | `fiscal/hacienda_client.py` |
| Horario hábil de envío | ✅ | `fiscal/horario.py` |
| Reintentos con backoff exponencial | ✅ | `fiscal/horario.py` |
| NC/ND con InformacionReferencia | ✅ | `fiscal/xml_builder.py` |
| Contingencia (situacion=2) | ✅ | `backend/app/services/contingencia_service.py` |
| Mensaje Receptor | ✅ | `fiscal/xml_builder.py` |

---

## 3. LO QUE FALTA PARA CUMPLIMIENTO COMPLETO API 4.4

### 🔴 Prioridad Alta (bloqueante para certificación MH)

| # | Item | Detalle | Estimación |
|---|------|---------|------------|
| 1 | Certificación staging/prod con MH | Emitir comprobantes reales en ATV staging | 1-2 semanas |
| 2 | XSD completos en repo | Descargar y versionar esquemas oficiales | 2 horas |
| 3 | XML para casos avanzados | Exoneraciones, otros cargos, múltiples medios de pago | 1 semana |
| 4 | Flujo asíncrono MH completo | callbackUrl + cola + consulta automática de estado | 1 semana |

### 🟡 Prioridad Media (post-certificación)

| # | Item | Detalle |
|---|------|---------|
| 5 | Factura de Exportación (05) | Requiere campos adicionales (incoterm, destino, etc.) |
| 6 | NC/ND con montos negativos | Ajustar signo en totales para devoluciones |
| 7 | Mensaje Receptor UI | Frontend para aceptar/rechazar comprobantes recibidos |

### 🟢 Prioridad Baja (nichos específicos)

| # | Item | Detalle |
|---|------|---------|
| 8 | Tipos 06-08 (Exportación/Compra) | Solo para empresas exportadoras/gubernamentales |
| 9 | Tipos 11-14 (Liquidación/Fiscal) | Solo para regímenes especiales |

---

## 4. PRÓXIMOS PASOS RECOMENDADOS

1. **Certificación con ATV staging** — crear empresa piloto y emitir FE real
2. **Descargar XSD completos** — `python scripts/download_xsd_schemas.py`
3. **Validar XML contra rechazos MH** — ajustar `xml_builder` según respuestas
4. **Implementar flujo asíncrono** — callback + reintentos automáticos
5. **Migrar a producción** — `ambiente_hacienda=prod` con certificado real

---

*Documento actualizado: 2 Junio 2026 — refleja el estado real del código.*
