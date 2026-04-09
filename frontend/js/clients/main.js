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
    // Si la ruta está vacía (index), asume la página de clientes.
    if (!ruta) ruta = 'clientes.html'; 
    
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


// =============================================================
// FUNCIONES DE GESTIÓN DE CLIENTES
// =============================================================

/**
 * Guarda un nuevo cliente o actualiza uno existente
 */
function guardarCliente() {
    const nombre = document.getElementById('cliente-nombre').value.trim();
    const cedula = document.getElementById('cliente-cedula').value.trim();
    const telefono = document.getElementById('cliente-telefono').value.trim();
    const email = document.getElementById('cliente-email').value.trim();
    const direccion = document.getElementById('cliente-direccion').value.trim();

    // Validación básica
    if (!nombre || !cedula || !telefono || !email || !direccion) {
        alert('❌ Por favor complete todos los campos requeridos.');
        return;
    }

    // Validar email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('❌ Por favor ingrese un correo electrónico válido.');
        return;
    }

    // Aquí iría la llamada al backend para guardar el cliente
    console.log('Guardando cliente:', { nombre, cedula, telefono, email, direccion });
    
    alert('✅ Cliente guardado exitosamente');
    limpiarFormularioCliente();
}

/**
 * Cancela la edición y limpia el formulario
 */
function cancelarCliente() {
    limpiarFormularioCliente();
}

/**
 * Limpia todos los campos del formulario de cliente
 */
function limpiarFormularioCliente() {
    document.getElementById('cliente-nombre').value = '';
    document.getElementById('cliente-cedula').value = '';
    document.getElementById('cliente-telefono').value = '';
    document.getElementById('cliente-email').value = '';
    document.getElementById('cliente-direccion').value = '';
}

// =============================================================
// FUNCIONES DE IMPORTACIÓN MASIVA DE CLIENTES
// =============================================================

let archivoExcelSeleccionado = null;

/**
 * Descarga la plantilla Excel para importar clientes
 */
function descargarPlantillaClientes() {
    // Crear datos de ejemplo para la plantilla
    const plantilla = [
        ['Nombre', 'Cédula', 'Teléfono', 'Email', 'Dirección'],
        ['Empresa Ejemplo S.A.', '3-101-123456', '8888-1234', 'ejemplo@empresa.com', 'San José, Centro'],
        ['Cliente Demo', '1-1234-5678', '8765-4321', 'demo@cliente.com', 'Alajuela, Centro'],
        ['', '', '', '', ''] // Fila vacía para que el usuario complete
    ];

    // Convertir a CSV (formato simple)
    const csv = plantilla.map(row => row.join(',')).join('\n');
    
    // Crear blob y descargar
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'plantilla_clientes.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log('✅ Plantilla de clientes descargada');
}

/**
 * Maneja la selección del archivo Excel
 */
function subirArchivoClientes(input) {
    const file = input.files[0];
    
    if (!file) {
        archivoExcelSeleccionado = null;
        document.getElementById('excel-file-name').textContent = 'Ningún archivo seleccionado';
        document.getElementById('btn-procesar-excel').disabled = true;
        return;
    }

    // Validar extensión
    const extension = file.name.split('.').pop().toLowerCase();
    if (!['xlsx', 'xls', 'csv'].includes(extension)) {
        alert('❌ Por favor seleccione un archivo Excel válido (.xlsx, .xls o .csv)');
        input.value = '';
        archivoExcelSeleccionado = null;
        document.getElementById('excel-file-name').textContent = 'Ningún archivo seleccionado';
        document.getElementById('btn-procesar-excel').disabled = true;
        return;
    }

    // Validar tamaño (máx 5MB)
    if (file.size > 5 * 1024 * 1024) {
        alert('❌ El archivo es demasiado grande. Tamaño máximo: 5MB');
        input.value = '';
        archivoExcelSeleccionado = null;
        document.getElementById('excel-file-name').textContent = 'Ningún archivo seleccionado';
        document.getElementById('btn-procesar-excel').disabled = true;
        return;
    }

    archivoExcelSeleccionado = file;
    document.getElementById('excel-file-name').textContent = file.name;
    document.getElementById('btn-procesar-excel').disabled = false;
    
    console.log('✅ Archivo seleccionado:', file.name);
}

/**
 * Procesa e importa el archivo de clientes
 */
async function procesarArchivoClientes() {
    if (!archivoExcelSeleccionado) {
        alert('❌ Por favor seleccione un archivo primero');
        return;
    }

    const btnProcesar = document.getElementById('btn-procesar-excel');
    const textoOriginal = btnProcesar.innerHTML;
    
    btnProcesar.disabled = true;
    btnProcesar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';

    try {
        // Leer el archivo como texto (para CSV)
        const texto = await leerArchivoComoTexto(archivoExcelSeleccionado);
        
        // Parsear CSV
        const lineas = texto.split('\n').filter(linea => linea.trim());
        
        if (lineas.length < 2) {
            throw new Error('El archivo está vacío o no tiene datos válidos');
        }

        // Saltar la primera línea (encabezados)
        const clientesImportados = [];
        
        for (let i = 1; i < lineas.length; i++) {
            const campos = lineas[i].split(',').map(c => c.trim());
            
            if (campos.length >= 5 && campos[0] && campos[1]) {
                clientesImportados.push({
                    nombre: campos[0],
                    cedula: campos[1],
                    telefono: campos[2],
                    email: campos[3],
                    direccion: campos[4]
                });
            }
        }

        if (clientesImportados.length === 0) {
            throw new Error('No se encontraron clientes válidos en el archivo');
        }

        // Aquí iría la llamada al backend para guardar múltiples clientes
        console.log('Clientes a importar:', clientesImportados);
        
        alert(`✅ Se importaron ${clientesImportados.length} clientes exitosamente`);
        
        // Limpiar
        document.getElementById('excel-upload').value = '';
        archivoExcelSeleccionado = null;
        document.getElementById('excel-file-name').textContent = 'Ningún archivo seleccionado';
        btnProcesar.disabled = true;
        btnProcesar.innerHTML = textoOriginal;
        
    } catch (error) {
        console.error('Error al procesar archivo:', error);
        alert('❌ Error al procesar el archivo: ' + error.message);
        btnProcesar.disabled = false;
        btnProcesar.innerHTML = textoOriginal;
    }
}

/**
 * Lee un archivo como texto
 */
function leerArchivoComoTexto(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(new Error('Error al leer el archivo'));
        reader.readAsText(file, 'UTF-8');
    });
}
