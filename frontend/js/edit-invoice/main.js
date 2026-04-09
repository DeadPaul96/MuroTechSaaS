/* --- Funciones Globales (Comunes a todas las páginas) --- */
function irA(url) {
    window.location.href = url;
}

function cerrarSesion() {
    if (confirm('¿Cerrar sesión?')) {
        irA('inicioSesion.html');
    }
}

function mostrarBusqueda() {
    const elemento = document.querySelector('.busqueda-global');
    if (elemento) elemento.classList.toggle('visible');
    else alert('Buscar (placeholder)');
}

function mostrarNotificaciones() {
    alert('Notificaciones (placeholder)');
}

/* --- Funciones Específicas de Página --- */

/**
 * Lógica que SOLO debe ejecutarse en la página de facturación (si tuviera el slider de impuestos).
 */
function initBillingPage() {
    const tarifa = document.getElementById('tarifa-impuesto');
    const salidaTarifa = document.getElementById('tarifa-output');

    // Si los elementos existen, añade los listeners
    if (tarifa && salidaTarifa) {
        tarifa.addEventListener('input', (evento) => {
            salidaTarifa.value = evento.target.value + '%';
        });
        // Settear valor inicial al cargar
        salidaTarifa.value = tarifa.value + '%';
    }
}

/**
 * Marca el botón activo en el sidebar (si existe).
 */
function marcarSidebarActivo() {
    let ruta = window.location.pathname.split('/').pop();
    ruta = ruta.split('?')[0].split('#')[0];
    if (!ruta) ruta = 'index.html'; // Fallback para la raíz

    const botones = document.querySelectorAll('.sidebar-btn[data-target]');
    if (botones.length > 0) {
        botones.forEach(boton => {
            const destino = boton.getAttribute('data-target');
            if (!destino) return;
            if (destino === ruta) {
                boton.classList.add('active');
            } else {
                boton.classList.remove('active');
            }
        });
    }
}

/**
 * Inicializa el fondo de tiles interactivos (si existe).
 */
function initTilesInteractive() {
    const container = document.getElementById('tiles');
    if (!container) return;

    // Lógica para calcular la cuadrícula
    let tileSize = 26;
    let columns = 0;
    let rows = 0;
    let tiles = [];
    let moveThrottle = null; 

    function generateTiles() {
        columns = Math.floor(document.body.clientWidth / tileSize);
        rows = Math.floor(document.body.clientHeight / tileSize);
        container.style.setProperty('--columns', columns);
        container.style.setProperty('--rows', rows);

        const fragment = document.createDocumentFragment();
        tiles = [];
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < columns; c++) {
                const tile = document.createElement('div');
                tile.className = 'tile';
                tile.dataset.r = r;
                tile.dataset.c = c;
                tile._releaseTimeout = null; 
                fragment.appendChild(tile);
                tiles.push(tile);
            }
        }

        container.innerHTML = '';
        container.appendChild(fragment);
    }

    function onPointerMove(e) {
        if (!container) return;

        const { clientX: x, clientY: y } = e.touches ? e.touches[0] : e;
        const cx = Math.floor(x / tileSize);
        const cy = Math.floor(y / tileSize);

        const radius = 3; 

        for (let r = cy - radius; r <= cy + radius; r++) {
            for (let c = cx - radius; c <= cx + radius; c++) {
                const tileIndex = r * columns + c;
                const tile = tiles[tileIndex];

                if (tile) {
                    const dx = c - cx;
                    const dy = r - cy;
                    const distSq = dx * dx + dy * dy;

                    if (distSq <= radius * radius) {
                        const intensity = 1 - Math.sqrt(distSq) / radius;
                        
                        tile.style.backgroundColor = `rgba(37, 99, 235, ${intensity * 0.3})`;
                        tile.style.boxShadow = `0 0 ${intensity * 10}px rgba(37, 99, 235, ${intensity * 0.5})`;

                        clearTimeout(tile._releaseTimeout);
                        tile._releaseTimeout = setTimeout(() => {
                            tile.style.backgroundColor = '';
                            tile.style.boxShadow = '';
                            tile._releaseTimeout = null;
                        }, 350);
                    }
                }
            }
        }
    }

    function onPointerLeave() {
        tiles.forEach(t => {
            t.style.backgroundColor = '';
            t.style.boxShadow = '';
        });
    }

    // Handlers
    generateTiles();
    
    window.addEventListener('pointermove', (e) => {
        if (moveThrottle) return;
        moveThrottle = setTimeout(() => moveThrottle = null, 12);
        onPointerMove(e);
    });
    window.addEventListener('touchmove', (e) => {
        onPointerMove(e);
    }, {passive:true});
    window.addEventListener('pointerleave', onPointerLeave);
    
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(generateTiles, 250);
    });
}

/*
  =============================================================
  INICIALIZADOR PRINCIPAL
  =============================================================
*/
document.addEventListener('DOMContentLoaded', () => {
    
    // Funciones que se ejecutan en TODAS las páginas
    marcarSidebarActivo();
    initTilesInteractive(); 

    // Funciones que SOLO se ejecutan en páginas específicas
    initBillingPage(); 
    
});
