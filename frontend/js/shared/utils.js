// Utilidades compartidas para todo el sistema

document.addEventListener('DOMContentLoaded', () => {
    // Inyectar blobs de fondo animados automáticamente si no existen
    if (!document.querySelector('.bg-blobs')) {
        const blobContainer = document.createElement('div');
        blobContainer.className = 'bg-blobs';
        blobContainer.innerHTML = `
            <div class="blob"></div>
            <div class="blob blob-2"></div>
            <div class="blob blob-3"></div>
        `;
        document.body.prepend(blobContainer);
    }
});
// Función de navegación global
function irA(url) {
    if (window.isDirty) {
        const isBilling = typeof window.saveDraftManual === 'function';
        
        Swal.fire({
            title: '¿Deseas salir del sitio?',
            text: isBilling 
                ? 'Tienes cambios sin guardar. Te recomendamos guardar un borrador antes de salir para no perder tu progreso.' 
                : 'Es posible que los cambios que implementaste no se puedan guardar.',
            icon: 'warning',
            showCancelButton: true,
            showDenyButton: isBilling,
            confirmButtonColor: '#1e40af',
            denyButtonColor: '#10b981',
            cancelButtonColor: '#64748b',
            confirmButtonText: 'Sí, salir sin guardar',
            denyButtonText: '<i class="fas fa-save"></i> Guardar y Salir',
            cancelButtonText: 'Cancelar',
            reverseButtons: true,
            background: '#ffffff',
            customClass: {
                popup: 'premium-swal-popup'
            }
        }).then((result) => {
            if (result.isConfirmed) {
                window.isDirty = false;
                ejecutarNavegacion(url);
            } else if (result.isDenied && isBilling) {
                // Guardar borrador y luego navegar
                window.saveDraftManual();
                window.isDirty = false;
                setTimeout(() => ejecutarNavegacion(url), 500);
            }
        });
    } else {
        ejecutarNavegacion(url);
    }
}

function ejecutarNavegacion(url) {
    const main = document.querySelector('.module-content, .dashboard-full-width, main, .register-card');
    if (main) {
        main.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
        main.style.opacity = '0';
        main.style.transform = 'translateY(15px) scale(0.98)';
        main.style.filter = 'blur(10px)';
        
        setTimeout(() => {
            window.location.href = url;
        }, 300);
    } else {
        window.location.href = url;
    }
}

// Inicializar tiles de fondo (efecto visual)
function initializeTiles() {
    const tilesContainer = document.getElementById('tiles');
    if (!tilesContainer) return;

    const columns = Math.floor(window.innerWidth / 100);
    const rows = Math.floor(window.innerHeight / 100);
    
    tilesContainer.style.setProperty('--columns', columns);
    tilesContainer.style.setProperty('--rows', rows);
    
    const totalTiles = columns * rows;
    
    for (let i = 0; i < totalTiles; i++) {
        const tile = document.createElement('div');
        tile.classList.add('tile');
        tilesContainer.appendChild(tile);
    }

    // Efecto hover en tiles
    const tiles = document.querySelectorAll('.tile');
    tiles.forEach(tile => {
        tile.addEventListener('mouseenter', () => {
            tile.classList.add('active');
            setTimeout(() => tile.classList.remove('active'), 600);
        });
    });
}

// Validar email
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Validar contraseña (mínimo 8 caracteres, mayúsculas, minúsculas y números)
function validatePassword(password) {
    const minLength = password.length >= 8;
    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasNumber = /\d/.test(password);
    
    return minLength && hasUpper && hasLower && hasNumber;
}

// Formatear número de cédula
function formatCedula(cedula, tipo) {
    cedula = cedula.replace(/\D/g, '');
    
    switch(tipo) {
        case '01': // Física
            if (cedula.length === 9) {
                return cedula.replace(/(\d{1})(\d{4})(\d{4})/, '$1-$2-$3');
            }
            break;
        case '02': // Jurídica
            if (cedula.length === 10) {
                return cedula.replace(/(\d{1})(\d{3})(\d{6})/, '$1-$2-$3');
            }
            break;
        case '03': // DIMEX
        case '04': // NITE
            if (cedula.length === 11 || cedula.length === 12) {
                return cedula.replace(/(\d{4})(\d{4})(\d{3,4})/, '$1-$2-$3');
            }
            break;
    }
    
    return cedula;
}

// Formatear moneda (colones costarricenses)
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-CR', {
        style: 'currency',
        currency: 'CRC',
        minimumFractionDigits: 2
    }).format(amount);
}

// Formatear fecha
function formatDate(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }
    
    return new Intl.DateTimeFormat('es-CR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(date);
}

// Formatear fecha y hora
function formatDateTime(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }
    
    return new Intl.DateTimeFormat('es-CR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    }).format(date);
}

// Mostrar mensaje de éxito
function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: 'Éxito',
        text: message,
        confirmButtonColor: '#1e40af'
    });
}

// Mostrar mensaje de error
function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        confirmButtonColor: '#ef4444'
    });
}

// Mostrar loading
function showLoading(show = true) {
    let loader = document.getElementById('global-loader');
    
    if (!loader && show) {
        loader = document.createElement('div');
        loader.id = 'global-loader';
        loader.innerHTML = `
            <div class="loader-overlay">
                <div class="loader-spinner"></div>
                <p>Cargando...</p>
            </div>
        `;
        document.body.appendChild(loader);
    } else if (loader && !show) {
        loader.remove();
    }
}

// Hacer petición HTTP con manejo de errores
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
			}
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Error en la petición');
        }

        return await response.json();
    } catch (error) {
        console.error('Error en fetchAPI:', error);
        throw error;
    }
}

// Debounce para búsquedas
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Validar número de teléfono costarricense
function validatePhone(phone) {
    // Formato: 8 dígitos, comenzando con 2, 4, 5, 6, 7 u 8
    const re = /^[2-8]\d{7}$/;
    return re.test(phone.replace(/\D/g, ''));
}

// Formatear número de teléfono
function formatPhone(phone) {
    phone = phone.replace(/\D/g, '');
    if (phone.length === 8) {
        return phone.replace(/(\d{4})(\d{4})/, '$1-$2');
    }
    return phone;
}

// Cerrar sesión
function cerrarSesion() {
    Swal.fire({
        title: '¿Cerrar sesión?',
        text: "¿Está seguro que desea salir del sistema?",
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#1e40af',
        cancelButtonColor: '#64748b',
        confirmButtonText: 'Sí, salir',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            localStorage.clear();
            sessionStorage.clear();
            window.location.href = 'inicioSesion.html';
        }
    });
}

// Mostrar notificaciones
function mostrarNotificaciones() {
    Swal.fire({
        title: 'Notificaciones',
        text: 'No hay notificaciones nuevas en este momento.',
        icon: 'info',
        confirmButtonColor: '#1e40af'
    });
}

// Función para búsqueda por múltiples palabras (any word match)
function multiWordMatch(text, query) {
    if (!query) return true;
    const words = query.toLowerCase().split(/\s+/).filter(w => w.length > 0);
    const target = (text || '').toLowerCase();
    return words.every(word => target.includes(word));
}

// Exportar funciones si se usa como módulo
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        irA,
        initializeTiles,
        validateEmail,
        validatePassword,
        formatCedula,
        formatCurrency,
        formatDate,
        formatDateTime,
        showSuccess,
        showError,
        showLoading,
        fetchAPI,
        debounce,
        validatePhone,
        formatPhone,
        cerrarSesion,
        mostrarNotificaciones,
        multiWordMatch
    };
}
