/**
 * MUROTECH POS - Micro Base de Datos Simulada
 * Almacena información en el localStorage simulando un Backend real.
 */

(function () {
    const DB_KEY = 'murotech_mockdb_v2';

    // ─── SEMILLA DE DATOS (SEED) ────────────────────────────────────────────────
    const defaultData = {
        clientes: [
            { id: 1, tipoId: '01', identificacion: '116490332', nombre: 'Daniel Solís Vargas', correo: 'daniel@murotech.com', telefono: '8888-8888', movil: '', direccion: 'Oficinas Centrales', provincia: 'San José', canton: 'Escazú', distrito: 'Escazú', barrio: 'San Antonio', regimen: 'general' },
            { id: 2, tipoId: '02', identificacion: '3101123456', nombre: 'Tech Solutions S.A.', correo: 'info@techsolutions.cr', telefono: '2540-0000', movil: '', direccion: 'Industrial Park', provincia: 'Alajuela', canton: 'Alajuela', distrito: 'San José', barrio: 'El Coyol', regimen: 'general' },
            { id: 3, tipoId: '01', identificacion: '205550222', nombre: 'María García López', correo: 'maria.garcia@email.com', telefono: '', movil: '6000-1234', direccion: 'Condominio Las Flores, Casa 4', provincia: 'Heredia', canton: 'Heredia', distrito: 'San Francisco', barrio: 'Arias', regimen: 'simplificado' },
            { id: 4, tipoId: '02', identificacion: '3102444555', nombre: 'Importadora del Atlántico S.A', correo: 'ventas@importatlantico.com', telefono: '2777-1111', movil: '', direccion: 'Bodegas 15A', provincia: 'Limón', canton: 'Limón', distrito: 'Limón', barrio: 'Cieneguita', regimen: 'general' },
            { id: 5, tipoId: '01', identificacion: '207580198', nombre: 'Murotech Beta Tester', correo: 'tester@murotech.com', telefono: '2222-3333', movil: '8000-0000', direccion: 'Pruebas de Sistema', provincia: 'Cartago', canton: 'Cartago', distrito: 'Oriental', barrio: 'Centro', regimen: 'simplificado' }
        ],
        inventario: [
            // --- 10 PRODUCTOS (HARDWARE Y EQUIPOS) ---
            { id: 1, cabys: '4311000000000', codigo: 'LAP-HP-G8', descripcion: 'Computadores portátiles y dispositivos electrónicos portátiles', marca: 'HP', modelo: 'EliteBook 840 G8', caracteristicas: 'Core i7, 16GB RAM, 512GB SSD', unidadMedida: 'Unid', precio: 550000, margen: 25, impuesto: '13', precioVenta: 687500, stock: 12 },
            { id: 2, cabys: '4321190200000', codigo: 'MON-DE-4K', descripcion: 'Monitores y proyectores de pantalla plana LCD o LED', marca: 'Dell', modelo: 'UltraSharp U2723QE', caracteristicas: '27" 4K IPS, USB-C Hub', unidadMedida: 'Unid', precio: 320000, margen: 20, impuesto: '13', precioVenta: 384000, stock: 8 },
            { id: 3, cabys: '4321170800000', codigo: 'MOU-LOG-MX', descripcion: 'Dispositivos de entrada de datos (Ratones)', marca: 'Logitech', modelo: 'MX Master 3S', caracteristicas: 'Sensor 8K DPI, Silent Clicks', unidadMedida: 'Unid', precio: 45000, margen: 40, impuesto: '13', precioVenta: 63000, stock: 25 },
            { id: 4, cabys: '4321170600000', codigo: 'TEC-KY-K2', descripcion: 'Dispositivos de entrada de datos (Teclados)', marca: 'Keychron', modelo: 'K2 V2', caracteristicas: 'Mecánico Wireless, RGB, Gateron Brown', unidadMedida: 'Unid', precio: 55000, margen: 35, impuesto: '13', precioVenta: 74250, stock: 15 },
            { id: 5, cabys: '4320180300000', codigo: 'SSD-SAM-2T', descripcion: 'Unidades de almacenamiento de estado sólido (SSD)', marca: 'Samsung', modelo: '980 Pro 2TB', caracteristicas: 'NVMe Gen4, 7000MB/s', unidadMedida: 'Unid', precio: 85000, margen: 15, impuesto: '13', precioVenta: 97750, stock: 40 },
            { id: 6, cabys: '4320140200000', codigo: 'RAM-COR-32', descripcion: 'Módulos de memoria de acceso aleatorio (RAM)', marca: 'Corsair', modelo: 'Vengeance LPX 32GB', caracteristicas: 'DDR4 3600MHz (2x16GB)', unidadMedida: 'Unid', precio: 42000, margen: 20, impuesto: '13', precioVenta: 50400, stock: 30 },
            { id: 7, cabys: '4322260000000', codigo: 'NET-UB-UDM', descripcion: 'Equipo de red de datos (Routers/Switches)', marca: 'Ubiquiti', modelo: 'UniFi Dream Machine', caracteristicas: 'All-in-one Enterprise Console', unidadMedida: 'Unid', precio: 180000, margen: 22, impuesto: '13', precioVenta: 219600, stock: 5 },
            { id: 8, cabys: '4321210400000', codigo: 'PRN-EP-3250', descripcion: 'Impresoras de chorro de tinta (Inkjet)', marca: 'Epson', modelo: 'EcoTank L3250', caracteristicas: 'Multifuncional WiFi Tinta Continua', unidadMedida: 'Unid', precio: 115000, margen: 18, impuesto: '13', precioVenta: 135700, stock: 10 },
            { id: 9, cabys: '4319160900000', codigo: 'AUD-SON-XM5', descripcion: 'Dispositivos de salida de audio (Audífonos)', marca: 'Sony', modelo: 'WH-1000XM5', caracteristicas: 'Noise Cancelling, Platinum Silver', unidadMedida: 'Unid', precio: 195000, margen: 30, impuesto: '13', precioVenta: 253500, stock: 14 },
            { id: 10, cabys: '4522003010000', codigo: 'CAM-CAN-R6', descripcion: 'Cámaras fotográficas digitales profesionales', marca: 'Canon', modelo: 'EOS R6 Mark II', caracteristicas: 'Full Frame, 24.2 MP, 4K60p', unidadMedida: 'Unid', precio: 1450000, margen: 12, impuesto: '13', precioVenta: 1624000, stock: 3 },

            // --- 20 SERVICIOS (SOPORTE Y TI) ---
            { id: 11, cabys: '8311100000000', codigo: 'SVC-MANT-PC', descripcion: 'Servicios de gestión y soporte en tecnología de información', nombreServicio: 'Mantenimiento Preventivo PC', detalleServicio: 'Limpieza física, cambio pasta térmica y optimización', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 25000, stock: 0 },
            { id: 12, cabys: '8311100000000', codigo: 'SVC-NET-INS', descripcion: 'Servicios de instalación de redes de datos', nombreServicio: 'Instalación de Punto de Red', detalleServicio: 'Cableado cat6, jack RJ45 y certificación de punto', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 18000, stock: 0 },
            { id: 13, cabys: '8311300000000', codigo: 'SVC-CONS-TI', descripcion: 'Servicios de consultoría en informática', nombreServicio: 'Consultoría Técnica (Hora)', detalleServicio: 'Asesoría especializada en infraestructura y seguridad', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 45000, stock: 0 },
            { id: 14, cabys: '8314300000000', codigo: 'SVC-SOFT-DEV', descripcion: 'Servicios de diseño y desarrollo de software', nombreServicio: 'Desarrollo de Modulo Web', detalleServicio: 'Implementación de funcionalidades personalizadas', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 150000, stock: 0 },
            { id: 15, cabys: '8111150100000', codigo: 'SVC-VIR-CLE', descripcion: 'Servicios de limpieza de virus y malware', nombreServicio: 'Desinfección de Sistema', detalleServicio: 'Eliminación completa de amenazas y restauración', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 20000, stock: 0 },
            { id: 16, cabys: '8111150100000', codigo: 'SVC-FIRE-CFG', descripcion: 'Servicios de configuración de seguridad', nombreServicio: 'Configuración de Firewall', detalleServicio: 'Políticas de seguridad, redirecciones y VPN', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 35000, stock: 0 },
            { id: 17, cabys: '8311500000000', codigo: 'SVC-BKUP-CFG', descripcion: 'Servicios de respaldo y recuperación de datos', nombreServicio: 'Configuración de Backup Cloud', detalleServicio: 'Respaldo automático incremental en la nube', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 12000, stock: 0 },
            { id: 18, cabys: '8111181100000', codigo: 'SVC-RECO-DAT', descripcion: 'Servicios de recuperación de información', nombreServicio: 'Recuperación de Datos Perdidos', detalleServicio: 'Extracción de datos críticos de discos dañados', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 85000, stock: 0 },
            { id: 19, cabys: '8111181100000', codigo: 'SVC-OS-INST', descripcion: 'Servicios de instalación de sistemas operativos', nombreServicio: 'Instalación de Windows/Linux', detalleServicio: 'Incluye drivers, actualizaciones y configuración básica', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 15000, stock: 0 },
            { id: 20, cabys: '8311700000000', codigo: 'SVC-TRAIN-TI', descripcion: 'Servicios de capacitación en informática', nombreServicio: 'Capacitación de Personal', detalleServicio: 'Taller de 2 horas sobre herramientas digitales', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 60000, stock: 0 },
            { id: 21, cabys: '8111181100000', codigo: 'SVC-HIN-REPA', descripcion: 'Servicios de reparación física de hardware', nombreServicio: 'Reparación de Bisagras', detalleServicio: 'Ajuste y reconstrucción de anclajes de laptop', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 35000, stock: 0 },
            { id: 22, cabys: '8311100000000', codigo: 'SVC-HW-DIAG', descripcion: 'Servicios de diagnóstico de equipo', nombreServicio: 'Diagnóstico de Hardware', detalleServicio: 'Pruebas de estrés y detección de fallas', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 10000, stock: 0 },
            { id: 23, cabys: '8311100000000', codigo: 'SVC-SRV-MNT', descripcion: 'Servicios de montaje de servidores', nombreServicio: 'Rackeo de Equipos', detalleServicio: 'Instalación física en rack y peinado de cables', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 25000, stock: 0 },
            { id: 24, cabys: '8311300000000', codigo: 'SVC-MAIL-ADM', descripcion: 'Servicios de gestión de correo', nombreServicio: 'Gestión de Correo Corporativo', detalleServicio: 'Administración de tenants M365 o Google Workspace', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 4500, stock: 0 },
            { id: 25, cabys: '8311300000000', codigo: 'SVC-REM-SPT', descripcion: 'Servicios de soporte remoto', nombreServicio: 'Soporte Remoto Mensual', detalleServicio: 'Asistencia ilimitada via AnyDesk/TeamViewer', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 30000, stock: 0 },
            { id: 26, cabys: '8311100000000', codigo: 'SVC-AUD-SEC', descripcion: 'Servicios de auditoría de seguridad', nombreServicio: 'Penetration Testing Básico', detalleServicio: 'Escaneo de vulnerabilidades y reporte técnico', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 180000, stock: 0 },
            { id: 27, cabys: '8314300000000', codigo: 'SVC-CLOUD-ARC', descripcion: 'Servicios de diseño cloud', nombreServicio: 'Diseño de Arquitectura AWS', detalleServicio: 'Estructuración de VPC, Lambda y RDS', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 120000, stock: 0 },
            { id: 28, cabys: '8311100000000', codigo: 'SVC-CCTV-INST', descripcion: 'Servicios de seguridad electrónica', nombreServicio: 'Instalación de CCTV (Cámara)', detalleServicio: 'Montaje de cámara, cableado y configuración DVR', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 15000, stock: 0 },
            { id: 29, cabys: '8311300000000', codigo: 'SVC-VOIP-CFG', descripcion: 'Servicios de telefonía IP', nombreServicio: 'Configuración Central VoIP', detalleServicio: 'Parametrización de extensiones e IVR', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 55000, stock: 0 },
            { id: 30, cabys: '8311100000000', codigo: 'SVC-LAP-SCRE', descripcion: 'Servicios de cambio de pantalla', nombreServicio: 'Reemplazo Pantalla Laptop', detalleServicio: 'Mano de obra para cambio de panel LED/LCD', unidadMedida: 'Svc', precio: 0, margen: 100, impuesto: '13', precioVenta: 18000, stock: 0 }
        ],
        facturas: [
            { id: 'FE-001000010100000001', clienteId: 2, clienteNombre: 'Tech Solutions S.A.', monto: 655400.00, estado: 'Pagada', fecha: '2026-04-01T10:30:00', xml: true },
            { id: 'FE-001000010100000002', clienteId: 4, clienteNombre: 'Importadora del Atlántico S.A', monto: 125000.00, estado: 'Pagada', fecha: '2026-04-03T14:15:00', xml: true },
            { id: 'FE-001000010100000003', clienteId: 1, clienteNombre: 'Daniel Solís Vargas', monto: 224250.00, estado: 'Pagada', fecha: '2026-04-05T09:00:00', xml: true },
            { id: 'FE-001000010100000004', clienteId: 3, clienteNombre: 'María García López', monto: 50000.00, estado: 'Pendiente', fecha: '2026-04-06T16:45:00', xml: true },
            { id: 'TE-001000010100000005', clienteId: 5, clienteNombre: 'Murotech Beta Tester', monto: 10400.00, estado: 'Pagada', fecha: '2026-04-07T11:20:00', xml: true },
            { id: 'FE-001000010100000006', clienteId: 2, clienteNombre: 'Tech Solutions S.A.', monto: 85000.00, estado: 'Pagada', fecha: '2026-04-08T15:20:00', xml: true },
            { id: 'FE-001000010100000007', clienteId: 1, clienteNombre: 'Daniel Solís Vargas', monto: 32000.00, estado: 'Pagada', fecha: '2026-04-08T17:10:00', xml: true }
        ],
        compras: [
            { id: 1, fecha: '2026-04-01T08:00:00', proveedor: 'Distribuidora Global S.A.', concepto: 'Lote de Laptops Core i7', montoNeto: 5000000, iva: 650000, total: 5650000, categoria: 'Equipos' },
            { id: 2, fecha: '2026-04-02T11:30:00', proveedor: 'Insumos Tecnológicos CR', concepto: 'Monitores y Accesorios', montoNeto: 1200000, iva: 156000, total: 1356000, categoria: 'Equipos' },
            { id: 3, fecha: '2026-04-04T15:20:00', proveedor: 'Servicios de Alquiler S.A.', concepto: 'Mensualidad Oficinas', montoNeto: 450000, iva: 58500, total: 508500, categoria: 'Servicios' },
            { id: 4, fecha: '2026-04-05T10:00:00', proveedor: 'Papelería El Norte', concepto: 'Suministros de Oficina', montoNeto: 25000, iva: 3250, total: 28250, categoria: 'Suministros' }
        ],
        cotizaciones: [
            { id: 'COT-1001', fecha: '2026-04-02T10:00:00', clienteNombre: 'Tech Solutions S.A.', vencimiento: '2026-04-15', monto: 1250000, estado: 'Enviada' },
            { id: 'COT-1002', fecha: '2026-04-05T14:30:00', clienteNombre: 'Banco Nacional (Suministros)', vencimiento: '2026-04-20', monto: 450000, estado: 'Pendiente' },
            { id: 'COT-1003', fecha: '2026-04-07T09:15:00', clienteNombre: 'Daniel Solís Vargas', vencimiento: '2026-04-22', monto: 75000, estado: 'Aceptada' }
        ],
        notificaciones: [
            { id: 1, tipo: 'hacienda', icono: 'fas fa-university', titulo: 'Factura FE-000249 aceptada', desc: 'Hacienda confirmó la recepción y aceptación del comprobante.', leida: false, fecha: new Date(Date.now() - 5*60000).toISOString() },
            { id: 2, tipo: 'sistema', icono: 'fas fa-sync-alt', titulo: 'Actualización del sistema disponible', desc: 'Nueva versión v6.2 con mejoras de rendimiento y seguridad.', leida: false, fecha: new Date(Date.now() - 2*3600000).toISOString() },
            { id: 3, tipo: 'inventario', icono: 'fas fa-exclamation', titulo: 'Stock bajo: Laptops y portátiles', desc: 'Quedan 3 unidades. Se recomienda reabastecer pronto.', leida: false, fecha: new Date(Date.now() - 5*3600000).toISOString() }
        ]
    };

    // ─── INICIALIZACIÓN ────────────────────────────────────────────────────────
    function initDB() {
        const stored = localStorage.getItem(DB_KEY);
        if (!stored) {
            console.log("MockDB: Inicializando por primera vez...");
            localStorage.setItem(DB_KEY, JSON.stringify(defaultData));
            return defaultData;
        }
        return JSON.parse(stored);
    }

    let memoryDB = initDB();

    function persist() {
        localStorage.setItem(DB_KEY, JSON.stringify(memoryDB));
    }

    // ─── MÉTODOS PÚBLICOS ──────────────────────────────────────────────────────
    window.muroDB = {
        // --- Utils Generales ---
        limpiarYReiniciar: function() {
            localStorage.removeItem(DB_KEY);
            memoryDB = initDB();
            console.log("MockDB Reiniciado a valores de fábrica.");
        },

        // --- Clientes ---
        getClientes: function() {
            return memoryDB.clientes;
        },
        addCliente: function(cliente) {
            cliente.id = Date.now(); // fake ID
            memoryDB.clientes.push(cliente);
            persist();
        },
        updateCliente: function(id, data) {
            const idx = memoryDB.clientes.findIndex(c => c.id === id);
            if (idx !== -1) {
                memoryDB.clientes[idx] = { ...memoryDB.clientes[idx], ...data };
                persist();
            }
        },
        deleteCliente: function(id) {
            memoryDB.clientes = memoryDB.clientes.filter(c => c.id !== id);
            persist();
        },

        // --- Inventario ---
        getProductos: function() {
            return memoryDB.inventario;
        },
        addProducto: function(prod) {
            prod.id = Date.now();
            memoryDB.inventario.push(prod);
            persist();
        },
        updateProducto: function(id, data) {
            const idx = memoryDB.inventario.findIndex(p => p.id === id);
            if (idx !== -1) {
                memoryDB.inventario[idx] = { ...memoryDB.inventario[idx], ...data };
                persist();
            }
        },
        deleteProducto: function(id) {
            memoryDB.inventario = memoryDB.inventario.filter(p => p.id !== id);
            persist();
        },

        // --- Facturas & Dashboard ---
        getFacturas: function() {
            return memoryDB.facturas.sort((a,b) => new Date(b.fecha) - new Date(a.fecha)); // Mas recientes primero
        },
        getCompras: function() {
            return (memoryDB.compras || []).sort((a,b) => new Date(b.fecha) - new Date(a.fecha));
        },
        getCotizaciones: function() {
            return (memoryDB.cotizaciones || []).sort((a,b) => new Date(b.fecha) - new Date(a.fecha));
        },
        updateFactura: function(id, data) {
            const idx = memoryDB.facturas.findIndex(f => f.id === id);
            if (idx !== -1) {
                memoryDB.facturas[idx] = { ...memoryDB.facturas[idx], ...data };
                persist();
            }
        },
        addFactura: function(f) {
            memoryDB.facturas.unshift(f);
            persist();
        },
        getMetricasDashboard: function() {
            const facturas = memoryDB.facturas;
            
            const totalEmitidas = facturas.length;
            const ingresos = facturas.filter(f => f.estado === 'Pagada').reduce((sum, f) => sum + f.monto, 0);
            const cantidadClientes = memoryDB.clientes.length;
            
            // Format money
            const ingresosAcortados = ingresos > 1000000 
                ? '₡' + (ingresos/1000000).toFixed(1) + 'M' 
                : '₡' + ingresos.toLocaleString();

            return {
                facturasEmitidas: totalEmitidas,
                ingresosTotales: ingresosAcortados,
                clientesActivos: cantidadClientes,
                tasaConversion: '94.2%'
            };
        },

        // --- Notificaciones ---
        getNotificaciones: function() {
            return memoryDB.notificaciones;
        },
        marcarTodasLeidas: function() {
            memoryDB.notificaciones.forEach(n => n.leida = true);
            persist();
        },

        // --- Búsquedas Optimizadas ---
        getClientByNumId: function(numId) {
            return memoryDB.clientes.find(c => c.identificacion === numId);
        },
        getProductByQuery: function(q) {
            if (!q) return null;
            q = q.toLowerCase();
            return memoryDB.inventario.find(p => 
                (p.descripcion||'').toLowerCase().includes(q) || 
                (p.codigo||'').toLowerCase().includes(q)
            );
        }
    };
})();
