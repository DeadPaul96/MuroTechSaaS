// Usar configuración centralizada
const CABYS_API_URL = `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.CABYS}`;

let timeoutBusquedaCABYS = null;
let resultadosCABYS = [];

/**
 * Inicializa el buscador de CABYS
 */
function inicializarBuscadorCABYS() {
    const inputBusqueda = document.querySelector('.cabys-search input');
    const btnBusqueda = document.querySelector('.cabys-search button');
    
    if (!inputBusqueda || !btnBusqueda) {
        console.warn('⚠️ Elementos de búsqueda CABYS no encontrados');
        return;
    }
    
    // Crear contenedor de resultados si no existe
    let contenedorResultados = document.querySelector('.cabys-resultados');
    if (!contenedorResultados) {
        contenedorResultados = document.createElement('div');
        contenedorResultados.className = 'cabys-resultados';
        inputBusqueda.parentElement.appendChild(contenedorResultados);
    }
    
    // Búsqueda en tiempo real mientras escribe
    inputBusqueda.addEventListener('input', (e) => {
        clearTimeout(timeoutBusquedaCABYS);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            ocultarResultadosCABYS();
            return;
        }
        
        // Debounce: esperar 400ms después de que deje de escribir
        timeoutBusquedaCABYS = setTimeout(() => {
            buscarCABYS(query);
        }, 400);
    });
    
    // Búsqueda al hacer click en el botón
    btnBusqueda.addEventListener('click', (e) => {
        e.preventDefault();
        const query = inputBusqueda.value.trim();
        if (query.length >= 2) {
            buscarCABYS(query);
        }
    });
    
    // Búsqueda al presionar Enter
    inputBusqueda.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = inputBusqueda.value.trim();
            if (query.length >= 2) {
                buscarCABYS(query);
            }
        }
    });
    
    // Cerrar resultados al hacer click fuera
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.cabys-search')) {
            ocultarResultadosCABYS();
        }
    });
    
    console.log('✅ Buscador de CABYS inicializado');
}

/**
 * Busca códigos CABYS en la API
 */
async function buscarCABYS(query) {
    try {
        mostrarCargandoCABYS();
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 segundos timeout
        
        const response = await fetch(`${CABYS_API_URL}/search?q=${encodeURIComponent(query)}&limit=15`, {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.results.length > 0) {
            resultadosCABYS = data.results;
            mostrarResultadosCABYS(data.results);
            console.log(`🔍 Encontrados ${data.count} códigos CABYS`);
        } else {
            mostrarSinResultadosCABYS(query);
        }
        
    } catch (error) {
        console.error('❌ Error al buscar CABYS:', error);
        if (error.name === 'AbortError') {
            mostrarErrorCABYS('Tiempo de espera agotado. Verifica que el servidor esté corriendo.');
        } else if (error.message.includes('Failed to fetch')) {
            mostrarErrorCABYS('No se puede conectar al servidor. Asegúrate de que esté corriendo en el puerto 5001.');
        } else {
            mostrarErrorCABYS(error.message);
        }
    }
}

/**
 * Muestra indicador de carga
 */
function mostrarCargandoCABYS() {
    const contenedor = document.querySelector('.cabys-resultados');
    if (!contenedor) return;
    
    contenedor.innerHTML = `
        <div class="cabys-loading">
            <i class="fas fa-spinner fa-spin"></i>
            <span>Buscando en catálogo CABYS...</span>
        </div>
    `;
    contenedor.style.display = 'block';
}

/**
 * Muestra los resultados de búsqueda
 */
function mostrarResultadosCABYS(resultados) {
    const contenedor = document.querySelector('.cabys-resultados');
    if (!contenedor) return;
    
    contenedor.innerHTML = `
        <div class="cabys-header">
            <span><i class="fas fa-barcode"></i> ${resultados.length} resultado${resultados.length !== 1 ? 's' : ''}</span>
            <button class="cabys-close" onclick="ocultarResultadosCABYS()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="cabys-lista">
            ${resultados.map((item, index) => `
                <div class="cabys-item" onclick="seleccionarCABYS(${index})" tabindex="0">
                    <div class="cabys-codigo">
                        <i class="fas fa-barcode"></i>
                        <strong>${item.codigo}</strong>
                    </div>
                    <div class="cabys-descripcion">${item.descripcion}</div>
                    <div class="cabys-impuesto">
                        <span class="badge-impuesto">IVA ${item.impuesto}%</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    contenedor.style.display = 'block';
    
    // Agregar navegación con teclado
    agregarNavegacionTeclado();
}

/**
 * Muestra mensaje cuando no hay resultados
 */
function mostrarSinResultadosCABYS(query) {
    const contenedor = document.querySelector('.cabys-resultados');
    if (!contenedor) return;
    
    contenedor.innerHTML = `
        <div class="cabys-sin-resultados">
            <i class="fas fa-search"></i>
            <p>No se encontraron resultados para "<strong>${query}</strong>"</p>
            <small>Intenta con otros términos de búsqueda</small>
        </div>
    `;
    contenedor.style.display = 'block';
}

/**
 * Muestra mensaje de error
 */
function mostrarErrorCABYS(mensaje) {
    const contenedor = document.querySelector('.cabys-resultados');
    if (!contenedor) return;
    
    contenedor.innerHTML = `
        <div class="cabys-error">
            <i class="fas fa-exclamation-triangle"></i>
            <p>Error al buscar CABYS</p>
            <small>${mensaje}</small>
            <small>Verifica tu conexión a internet o el estado del servidor.</small>
        </div>
    `;
    contenedor.style.display = 'block';
}

/**
 * Oculta los resultados de búsqueda
 */
function ocultarResultadosCABYS() {
    const contenedor = document.querySelector('.cabys-resultados');
    if (contenedor) {
        contenedor.style.display = 'none';
    }
}

/**
 * Selecciona un código CABYS y lo aplica al formulario
 */
function seleccionarCABYS(index) {
    const item = resultadosCABYS[index];
    
    if (!item) {
        console.error('❌ Item CABYS no encontrado');
        return;
    }
    
    // Llenar el campo de número CABYS
    const inputCABYS = document.getElementById('inv-cabys-numero');
    if (inputCABYS) {
        inputCABYS.value = item.codigo;
    }
    
    // Llenar el campo de búsqueda con la descripción
    const inputBusqueda = document.querySelector('.cabys-search input');
    if (inputBusqueda) {
        inputBusqueda.value = `${item.codigo} - ${item.descripcion}`;
    }
    
    // Si el campo de detalle está vacío, llenarlo con la descripción
    const inputDetalle = document.getElementById('inv-detalle');
    if (inputDetalle && !inputDetalle.value) {
        inputDetalle.value = item.descripcion;
    }
    
    // Ocultar resultados
    ocultarResultadosCABYS();
    
    // Mostrar notificación
    mostrarNotificacionCABYS(`✅ CABYS seleccionado: ${item.codigo}`, 'success');
    
    console.log('✅ CABYS seleccionado:', item);
}

/**
 * Agrega navegación con teclado (flechas arriba/abajo)
 */
function agregarNavegacionTeclado() {
    const items = document.querySelectorAll('.cabys-item');
    
    items.forEach((item, index) => {
        item.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' && index < items.length - 1) {
                e.preventDefault();
                items[index + 1].focus();
            } else if (e.key === 'ArrowUp' && index > 0) {
                e.preventDefault();
                items[index - 1].focus();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                seleccionarCABYS(index);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                ocultarResultadosCABYS();
            }
        });
    });
}

/**
 * Muestra notificación específica de CABYS
 */
function mostrarNotificacionCABYS(mensaje, tipo = 'info') {
    // Reutilizar la función de notificación global si existe
    if (typeof mostrarNotificacion === 'function') {
        mostrarNotificacion(mensaje, tipo);
        return;
    }
    
    // Si no existe, crear notificación simple
    const notif = document.createElement('div');
    notif.className = `notificacion-cabys notif-${tipo}`;
    notif.textContent = mensaje;
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${tipo === 'success' ? '#4caf50' : tipo === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notif);
    
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

/**
 * Verifica que el servidor CABYS esté disponible
 */
async function verificarServidorCABYS() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.HEALTH}`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000) 
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            console.log('✅ Servidor CABYS disponible');
            console.log(`   Modo: ${data.mode}`);
            console.log(`   Cache: ${data.cache_status}`);
            return true;
        } else {
            console.warn('⚠️ Servidor CABYS con problemas');
            return false;
        }
    } catch (error) {
        console.error('❌ Servidor no disponible:', error.message);
        return false;
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🔧 Inicializando módulo CABYS...');
    
    // Siempre inicializar el buscador
    inicializarBuscadorCABYS();
    
    // Verificar servidor en segundo plano
    setTimeout(async () => {
        const servidorDisponible = await verificarServidorCABYS();
        
        if (servidorDisponible) {
            console.log('✅ Módulo CABYS listo');
        } else {
            console.warn('⚠️ Módulo CABYS no disponible - Servidor no responde');
            // No mostrar notificación automáticamente, solo cuando intente buscar
        }
    }, 1000);
});
