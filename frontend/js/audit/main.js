/* --- Funciones Globales (Comunes a todas las páginas) --- */
function irA(url) {
    window.location.href = url;
}

function cerrarSesion() {
    if (confirm('¿Cerrar sesión?')) {
        irA('inicioSesion.html'); 
    }
}

function mostrarNotificaciones() {
    alert('Notificaciones (placeholder)');
}

/**
 * Marca el botón activo en el sidebar (basado en la URL actual).
 */
function marcarSidebarActivo() {
    let ruta = window.location.pathname.split('/').pop();
    ruta = ruta.split('?')[0].split('#')[0];
    // Ajuste: Si no hay ruta, o si está en la raíz, podría ser el index o el dashboard.
    if (!ruta) ruta = 'auditoria.html'; 
    
    document.querySelectorAll('.sidebar-btn').forEach(btn => {
        if (btn.getAttribute('data-target') === ruta) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// =============================================================
// L�"GICA DEL FONDO INTERACTIVO (Tiles)
// =============================================================
let tileSize = 26; // Tamaño del tile (24px) + gap (2px)
let columns = 0;
let rows = 0;
let tiles = [];
let moveThrottle = null; 

/**
 * Genera y dibuja los tiles en el contenedor #tiles.
 */
function generateTiles() {
    const tilesContainer = document.getElementById('tiles');
    if (!tilesContainer) return;
    
    columns = Math.floor(document.body.clientWidth / tileSize);
    rows = Math.floor(document.body.clientHeight / tileSize);
    tilesContainer.style.setProperty('--columns', columns);
    tilesContainer.style.setProperty('--rows', rows);

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

    tilesContainer.innerHTML = '';
    tilesContainer.appendChild(fragment);
}

/**
 * Maneja el movimiento del puntero para el efecto de brillo.
 */
function onPointerMove(e) {
    const tilesContainer = document.getElementById('tiles');
    if (!tilesContainer) return;

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
                    
                    tile.style.backgroundColor = `rgba(0, 255, 0, ${intensity * 0.3})`;
                    tile.style.boxShadow = `0 0 ${intensity * 10}px rgba(0, 255, 0, ${intensity * 0.8})`;

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

/**
 * Limpia el efecto cuando el puntero sale de la ventana.
 */
function onPointerLeave() {
    tiles.forEach(t => {
        t.style.backgroundColor = '';
        t.style.boxShadow = '';
    });
}

/**
 * Inicializa los tiles interactivos y los listeners.
 */
function initTilesInteractive() {
    const tilesContainer = document.getElementById('tiles');
    if (!tilesContainer) return;
    
    generateTiles();
    
    window.addEventListener('pointermove', (e) => {
        if (moveThrottle) return;
        moveThrottle = setTimeout(() => moveThrottle = null, 12); 
        onPointerMove(e);
    });
    window.addEventListener('touchmove', onPointerMove, {passive:true});
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
    
    marcarSidebarActivo();
    initTilesInteractive(); 
});
