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
            { id: 1, cabys: '4311000000000', codigo: 'LAP-001', descripcion: 'Laptop Profesional 14" Core i7 16GB RAM', categoria: 'Equipos', precio: 580000, margen: 20, impuesto: '13', precioVenta: 655400, stock: 15 },
            { id: 2, cabys: '4321190200000', codigo: 'MON-023', descripcion: 'Monitor LED 27" 4K IPS UHD', categoria: 'Equipos', precio: 195000, margen: 15, impuesto: '13', precioVenta: 224250, stock: 8 },
            { id: 3, cabys: '8311100000000', codigo: 'SRV-01', descripcion: 'Mantenimiento de Servidores', categoria: 'Servicios', precio: 0, margen: 100, impuesto: '13', precioVenta: 50000, stock: 999 },
            { id: 4, cabys: '4321170800000', codigo: 'MOU-05', descripcion: 'Mouse Inalámbrico Logitech', categoria: 'Accesorios', precio: 8000, margen: 30, impuesto: '13', precioVenta: 10400, stock: 30 },
            { id: 5, cabys: '4321170600000', codigo: 'TEC-08', descripcion: 'Teclado Mecánico RGB', categoria: 'Accesorios', precio: 25000, margen: 25, impuesto: '13', precioVenta: 31250, stock: 24 },
            { id: 6, cabys: '4323150000000', codigo: 'OF-365', descripcion: 'Licencia Suite Ofimática (Anual)', categoria: 'Software', precio: 45000, margen: 20, impuesto: '13', precioVenta: 54000, stock: 100 },
            { id: 7, cabys: '8111181100000', codigo: 'MANT-01', descripcion: 'Servicio Mantenimiento Preventivo PC', categoria: 'Servicios', precio: 0, margen: 100, impuesto: '13', precioVenta: 35000, stock: 999 },
            { id: 8, cabys: '8111150100000', codigo: 'CONS-01', descripcion: 'Consultoría en Seguridad de Redes (Hora)', categoria: 'Servicios', precio: 0, margen: 100, impuesto: '13', precioVenta: 40000, stock: 999 },
            { id: 9, cabys: '4320180300000', codigo: 'SSD-1TB', descripcion: 'Unidad de Estado Sólido (SSD) M.2 1TB', categoria: 'Componentes', precio: 50000, margen: 30, impuesto: '13', precioVenta: 65000, stock: 45 },
            { id: 10, cabys: '4320140200000', codigo: 'RAM-16', descripcion: 'Memoria RAM 16GB DDR4 3200MHz', categoria: 'Componentes', precio: 25000, margen: 28, impuesto: '13', precioVenta: 32000, stock: 50 },
            { id: 11, cabys: '4321210400000', codigo: 'IMP-HP', descripcion: 'Impresora Multifuncional Tinta Continua', categoria: 'Equipos', precio: 105000, margen: 19, impuesto: '13', precioVenta: 125000, stock: 12 },
            { id: 12, cabys: '4410310300000', codigo: 'TINT-BK', descripcion: 'Botella Tinta Negra Original 65ml', categoria: 'Suministros', precio: 5000, margen: 50, impuesto: '13', precioVenta: 7500, stock: 200 },
            { id: 13, cabys: '4319160900000', codigo: 'AUD-USB', descripcion: 'Audífonos Profesionales con Micrófono USB', categoria: 'Accesorios', precio: 20000, margen: 40, impuesto: '13', precioVenta: 28000, stock: 35 },
            { id: 14, cabys: '4323220200000', codigo: 'ANT-1YR', descripcion: 'Licencia Antivirus Endpoint Security 1 año', categoria: 'Software', precio: 12000, margen: 54, impuesto: '13', precioVenta: 18500, stock: 150 },
            { id: 15, cabys: '4322260800000', codigo: 'HDMI-3M', descripcion: 'Cable HDMI 2.0 de 3 Metros Trenzado', categoria: 'Accesorios', precio: 3000, margen: 100, impuesto: '13', precioVenta: 6000, stock: 80 }
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
