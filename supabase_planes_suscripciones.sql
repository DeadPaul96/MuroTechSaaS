-- ============================================
-- SCRIPT SQL: PLANES Y SUSCRIPCIONES
-- Para ejecutar en Supabase (PostgreSQL)
-- ============================================

-- Tabla: planes
CREATE TABLE IF NOT EXISTS planes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(50) NOT NULL,
    descripcion TEXT,
    precio_mensual DECIMAL(10, 2) NOT NULL,
    precio_anual DECIMAL(10, 2) NOT NULL,
    cuota_facturas INTEGER NOT NULL,
    usuarios_incluidos INTEGER DEFAULT 1,
    sucursales_incluidas INTEGER DEFAULT 1,
    tiene_api_hacienda BOOLEAN DEFAULT TRUE,
    tiene_firma_digital BOOLEAN DEFAULT FALSE,
    tiene_soporte BOOLEAN DEFAULT FALSE,
    tiene_reportes_avanzados BOOLEAN DEFAULT FALSE,
    tiene_multi_moneda BOOLEAN DEFAULT FALSE,
    orden INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: suscripciones
CREATE TABLE IF NOT EXISTS suscribciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id),
    plan_id UUID NOT NULL REFERENCES planes(id),
    
    estado VARCHAR(20) DEFAULT 'activa',  -- activa, suspendida, cancelada, trial
    tipo_cobro VARCHAR(10) DEFAULT 'mensual',  -- mensual, anual
    
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_vencimiento TIMESTAMP NOT NULL,
    fecha_cancelacion TIMESTAMP,
    
    facturas_usadas_mes INTEGER DEFAULT 0,
    periodo_facturacion TIMESTAMP,
    
    provider_pago VARCHAR(50),  -- stripe, paypal
    subscription_id_externo VARCHAR(100),
    ultimo_pago_id VARCHAR(100),
    ultimo_pago_estado VARCHAR(50),
    fecha_ultimo_pago TIMESTAMP,
    
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: pagos_suscripciones
CREATE TABLE IF NOT EXISTS pagos_suscripciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suscripcion_id UUID NOT NULL REFERENCES suscribciones(id),
    empresa_id UUID NOT NULL REFERENCES empresas(id),
    
    monto DECIMAL(10, 2) NOT NULL,
    moneda VARCHAR(3) DEFAULT 'CRC',
    tipo_cobro VARCHAR(10),
    
    provider VARCHAR(50),  -- stripe, paypal
    payment_id_externo VARCHAR(100),
    payment_method VARCHAR(50),
    
    estado VARCHAR(20) DEFAULT 'pendiente',  -- pendiente, completado, fallido, reembolsado
    descripcion TEXT,
    metadata_json TEXT,
    
    fecha_pago TIMESTAMP,
    fecha_procesado TIMESTAMP,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_suscripciones_empresa ON suscribciones(empresa_id);
CREATE INDEX IF NOT EXISTS idx_suscripciones_estado ON suscribciones(estado);
CREATE INDEX IF NOT EXISTS idx_pagos_suscripcion ON pagos_suscripciones(suscripcion_id);
CREATE INDEX IF NOT EXISTS idx_pagos_empresa ON pagos_suscripciones(empresa_id);
CREATE INDEX IF NOT EXISTS idx_planes_activos ON planes(is_active, orden);

-- Insertar planes por defecto
INSERT INTO planes (nombre, descripcion, precio_mensual, precio_anual, cuota_facturas, usuarios_incluidos, sucursales_incluidas, tiene_api_hacienda, tiene_firma_digital, tiene_soporte, tiene_reportes_avanzados, tiene_multi_moneda, orden) VALUES
(
    'Básico',
    'Ideal para pequeños negocios que inician su facturación electrónica. Incluye las funcionalidades esenciales para cumplir con la normativa 4.4 del Ministerio de Hacienda.',
    15000.00,
    150000.00,
    50,
    1,
    1,
    TRUE,
    FALSE,
    FALSE,
    FALSE,
    FALSE,
    1
),
(
    'Profesional',
    'Para negocios en crecimiento que necesitan más capacidad y herramientas avanzadas. Incluye firma digital y soporte básico.',
    35000.00,
    350000.00,
    200,
    3,
    2,
    TRUE,
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    2
),
(
    'Enterprise',
    'Solución completa para empresas con múltiples sucursales. Incluye reportes avanzados, soporte prioritario y todas las funcionalidades.',
    75000.00,
    750000.00,
    1000,
    10,
    5,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    3
),
(
    'Corporativo',
    'Para grandes empresas con necesidades específicas. Facturación ilimitada, múltiples sucursales, API dedicada y soporte 24/7.',
    150000.00,
    1500000.00,
    999999,
    999,
    999,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    4
) ON CONFLICT DO NOTHING;

-- Verificar inserción
SELECT nombre, precio_mensual, cuota_facturas FROM planes ORDER BY orden;