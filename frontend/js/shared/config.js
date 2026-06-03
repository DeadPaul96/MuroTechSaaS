/**
 * CONFIGURACIÓN CENTRALIZADA MUROTECH SaaS
 * Detecta automáticamente el entorno para funcionar en:
 *   - Desarrollo local (Flask sirve frontend + API en el mismo puerto)
 *   - Producción (frontend y API desplegados por separado)
 */

const CONFIG = {
    // Detectar automáticamente el entorno
    get API_BASE_URL() {
        const hostname = window.location.hostname;
        const isLocal = hostname === 'localhost' ||
                       hostname === '127.0.0.1' ||
                       hostname === '';

        if (isLocal) {
            // Si el frontend es servido por Flask (mismo origen), usar URL relativa
            if (window.location.port === '5001') {
                return '';  // Misma raíz — peticiones relativas (/api/...)
            }
            // Si se abre desde file:// u otro puerto, apuntar al backend
            return 'http://localhost:5001';
        } else {
            // URL de producción (Render)
            return 'https://murotechsaas-95ru.onrender.com';
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
        VERSION: '1.3.0',
        AUTHOR: 'MUROTECH Development Team'
    }
};

// Exportar para depuración
console.log(`%c 🚀 ${CONFIG.SYSTEM.NAME} v${CONFIG.SYSTEM.VERSION} inicializado`, 'color: #f97316; font-weight: bold;');
console.log(`📡 Modo: ${window.location.hostname === 'localhost' ? 'DESARROLLO (Local)' : 'PRODUCCIÓN (Cloud)'}`);
console.log(`🔗 API URL: ${CONFIG.API_BASE_URL || '(mismo origen)'}`);
