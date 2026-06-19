/**
 * CONFIGURACIÓN CENTRALIZADA MUROTECH SaaS
 * Detecta automáticamente el entorno para funcionar en:
 *   - Desarrollo local (Flask sirve frontend + API en el mismo puerto)
 *   - Producción (frontend y API desplegados por separado)
 */

const CONFIG = {
    get API_BASE_URL() {
        // Siempre apunta al backend local en puerto 5001
        return 'http://localhost:5001';
    },

    ENDPOINTS: {
        CABYS: '/api/cabys',
        INVENTARIO: '/api/inventario',
        CLIENTES: '/api/clientes',
        HEALTH: '/api/health'
    },

    SYSTEM: {
        NAME: 'MUROTECH Billing Platform',
        VERSION: '1.3.0',
        AUTHOR: 'MUROTECH Development Team'
    }
};

// Exportar para depuración
console.log(`%c 🚀 ${CONFIG.SYSTEM.NAME} v${CONFIG.SYSTEM.VERSION} inicializado`, 'color: #f97316; font-weight: bold;');
console.log(`📡 Modo: ${window.location.hostname === 'localhost' ? 'DESARROLLO (Local)' : 'PRODUCCIÓN (Cloud)'}`);
console.log(`🔗 API URL: ${CONFIG.API_BASE_URL || '(mismo origen)'}`);
