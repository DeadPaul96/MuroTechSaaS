/**
 * CONFIGURACIÓN CENTRALIZADA MUROTECH SaaS
 * Este archivo gestiona las variables de entorno para que el sistema funcione
 * tanto en desarrollo local como en el servidor de producción.
 */

const CONFIG = {
    // Detectar automáticamente el entorno
    get API_BASE_URL() {
        const isLocal = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' || 
                       window.location.hostname === '';
        
        if (isLocal) {
            return 'http://localhost:5001';
        } else {
            // URL de producción (Render)
            // IMPORTANTE: Cambiar esta URL cuando tengas el link de Render definitivo
            return 'https://murotechsaas.onrender.com';
        }
    },

    ENDPOINTS: {
        CABYS: '/api/cabys',
        INVENTARIO: '/api/inventario',
        CLIENTES: '/api/clientes',
        HEALTH: '/api/health'
    },

    SYSTEM: {
        NAME: 'MUROTECH Billing Platform',
        VERSION: '1.2.5-QA',
        AUTHOR: 'MUROTECH Development Team'
    }
};

// Exportar para depuración
console.log(`%c 🚀 ${CONFIG.SYSTEM.NAME} v${CONFIG.SYSTEM.VERSION} inicializado`, 'color: #f97316; font-weight: bold;');
console.log(`📡 Modo: ${window.location.hostname === 'localhost' ? 'DESARROLLO (Local)' : 'PRODUCCIÓN (Cloud)'}`);
console.log(`🔗 API URL: ${CONFIG.API_BASE_URL}`);
