/* --- Funciones Globales --- */
function irA(url) {
    window.location.href = url;
}

function cerrarSesion() {
    if (confirm('¿Está seguro que desea cerrar sesión?')) {
        // Limpiar datos de sesión
        localStorage.clear();
        sessionStorage.clear();
        // Redirigir a inicio de sesión
        irA('inicioSesion.html');
    }
}

function mostrarNotificaciones() {
    alert('Notificaciones (placeholder)');
}

/* --- Funciones Específicas de Página --- */

/**
 * Función para la página de inventario (Carga de imagen, validación, búsqueda).
 */
function initInventoryPage() {
    const imageUploadArea = document.getElementById('imageUploadArea');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');

    if (imageUploadArea && imageInput && imagePreview) {
        const uploadText = imageUploadArea.querySelector('span');
        const uploadIcon = imageUploadArea.querySelector('i');

        // Click para subir imagen
        imageUploadArea.addEventListener('click', () => {
            imageInput.click();
        });

        // Cambio de archivo
        imageInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                    if (uploadText) uploadText.style.display = 'none';
                    if (uploadIcon) uploadIcon.style.display = 'none';
                };
                reader.readAsDataURL(file);
            } else {
                // No molestar al usuario si cancela
                if(file) alert('Por favor, selecciona un archivo de imagen válido.');
            }
        });

        // Drag and drop
        imageUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            imageUploadArea.style.borderColor = 'var(--primary)';
            imageUploadArea.style.background = 'var(--primary-light)';
        });

        imageUploadArea.addEventListener('dragleave', () => {
            imageUploadArea.style.borderColor = 'var(--border-color)';
            imageUploadArea.style.background = 'var(--bg-main)';
        });

        imageUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            imageUploadArea.style.borderColor = 'rgba(0, 255, 0, 0.5)';
            imageUploadArea.style.background = 'rgba(34, 34, 34, 0.5)';
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('image/')) {
                imageInput.files = files;
                imageInput.dispatchEvent(new Event('change'));
            } else {
                alert('Por favor, suelta un archivo de imagen válido.');
            }
        });
    }

    // Validación de formulario
    const addItemForm = document.querySelector('.add-item-form');
    const addItemBtn = document.querySelector('.add-item-btn');
    
    if (addItemBtn && addItemForm) {
        addItemBtn.addEventListener('click', (e) => {
            e.preventDefault();
            
            const nombre = document.getElementById('inv-nombre');
            const precio = document.getElementById('inv-precio');
            
            if (!nombre || !nombre.value.trim()) {
                alert('Por favor, ingresa un nombre para el producto.');
                nombre.focus();
                return;
            }
            
            if (!precio || !precio.value.trim() || isNaN(parseFloat(precio.value))) {
                alert('Por favor, ingresa un precio válido.');
                precio.focus();
                return;
            }
            
            alert('Producto agregado al inventario correctamente.');
            
            // Limpiar formulario
            addItemForm.reset();
            if (imagePreview) {
                imagePreview.style.display = 'none';
                imagePreview.src = '#';
            }
            // (Asegurarse de que los elementos de texto/icono existan antes de usarlos)
            const uploadText = imageUploadArea ? imageUploadArea.querySelector('span') : null;
            const uploadIcon = imageUploadArea ? imageUploadArea.querySelector('i') : null;
            if (uploadText) uploadText.style.display = 'block';
            if (uploadIcon) uploadIcon.style.display = 'block';
        });
    }

    // Búsqueda en tiempo real
    const searchInput = document.querySelector('.list-controls .search-input input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const items = document.querySelectorAll('.item-card');
            
            items.forEach(item => {
                const itemName = item.querySelector('.item-name').textContent.toLowerCase();
                const itemType = item.querySelector('.item-type').textContent.toLowerCase();
                const itemDetail = item.querySelector('.item-detail').textContent.toLowerCase();
                
                if (itemName.includes(searchTerm) || 
                    itemType.includes(searchTerm) || 
                    itemDetail.includes(searchTerm)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
}

/**
 * Marca el botón activo en el sidebar.
 */
function marcarSidebarActivo() {
    let ruta = window.location.pathname.split('/').pop();
    ruta = ruta.split('?')[0].split('#')[0];
    if (!ruta) ruta = 'index.html';

    const botones = document.querySelectorAll('.sidebar-btn[data-target]');
    if (botones.length > 0) {
        botones.forEach(boton => {
            const destino = boton.getAttribute('data-target');
            if (!destino) return;
            // Marca 'inventario.html' como activo
            if (destino === 'inventario.html') {
                boton.classList.add('active');
            } else {
                boton.classList.remove('active');
            }
        });
    }
}

/**
 * Inicializa el fondo de tiles interactivos.
 */
function initTilesInteractive() {
    const container = document.getElementById('tiles');
    if (!container) return;

    let tiles = [];
    let cols = 0;
    let rows = 0;
    let moveThrottle = null;
    let resizeTimeout;

    function generateTiles() {
        if (tiles.length) {
            tiles.forEach(t => {
                if (t._releaseTimeout) clearTimeout(t._releaseTimeout);
            });
        }
        container.innerHTML = '';
        tiles = [];
        const tileSize = 24 + 2;
        cols = Math.ceil(window.innerWidth / tileSize);
        rows = Math.ceil(window.innerHeight / tileSize);
        
        if (cols === 0 || rows === 0 || !isFinite(cols) || !isFinite(rows)) {
            return;
        }

        const total = cols * rows;
        container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
        
        const fragment = document.createDocumentFragment();
        for (let i = 0; i < total; i++) {
            const el = document.createElement('div');
            el.className = 'tile';
            fragment.appendChild(el);
            tiles.push(el);
        }
        container.appendChild(fragment);
    }

    function onPointerMove(e) {
        const rect = container.getBoundingClientRect();
        const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
        const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;

        const tileWidth = rect.width / cols;
        const tileHeight = rect.height / rows;
        const cx = Math.floor(x / tileWidth);
        const cy = Math.floor(y / tileHeight);

        const radius = 3; 
        for (let dx = -radius; dx <= radius; dx++) {
            for (let dy = -radius; dy <= radius; dy++) {
                const nx = cx + dx;
                const ny = cy + dy;
                if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
                const idx = ny * cols + nx;
                const tile = tiles[idx];
                if (!tile) continue;
                const dist = Math.hypot(dx, dy);
                const intensity = Math.max(0, 1 - dist / (radius + 0.2));
                if (intensity > 0.15) {
                    if (tile._releaseTimeout) clearTimeout(tile._releaseTimeout);
                    tile.classList.add('active');
                    tile.style.transform = `scale(${1 + 0.15 * intensity})`;
                    const b = Math.round(15 + 240 * intensity);
                    tile.style.backgroundColor = `rgba(37, 99, 235, ${0.1 + 0.5 * intensity})`;
                    tile._releaseTimeout = setTimeout(() => {
                        tile.classList.remove('active');
                        tile.style.transform = '';
                        tile.style.backgroundColor = '';
                        tile._releaseTimeout = null;
                    }, 350);
                }
            }
        }
    }

    function onPointerLeave() {
        tiles.forEach(t => {
            t.classList.remove('active');
            t.style.transform = '';
            t.style.backgroundColor = '';
        });
    }

    generateTiles();
    
    window.addEventListener('pointermove', (e) => {
        if (moveThrottle) return;
        moveThrottle = setTimeout(() => moveThrottle = null, 12);
        onPointerMove(e);
    });
    window.addEventListener('touchmove', onPointerMove, {passive:true});
    window.addEventListener('pointerleave', onPointerLeave);
    
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(generateTiles, 250);
    });
}

/* Inicializador Principal */
document.addEventListener('DOMContentLoaded', () => {
    marcarSidebarActivo();
    initTilesInteractive();
    // Se eliminó initBillingPage()
    initInventoryPage(); // Se mantiene la función específica de inventario
});


// =============================================================
// FUNCIONES DE IMPORTACIÓN MASIVA DE INVENTARIO
// =============================================================

let archivoExcelInventarioSeleccionado = null;

/**
 * Descarga la plantilla Excel para importar productos/servicios
 */
function descargarPlantillaInventario() {
    // Crear datos de ejemplo para la plantilla
    const plantilla = [
        ['Tipo', 'Nombre', 'Modelo', 'Código', 'Precio', 'Detalle', 'Cantidad'],
        ['Producto', 'Laptop Dell', 'Inspiron 15', 'PROD001', '450000', 'Laptop 15 pulgadas', '10'],
        ['Servicio', 'Mantenimiento PC', 'N/A', 'SERV001', '35000', 'Limpieza y formateo', '1'],
        ['', '', '', '', '', '', ''] // Fila vacía para que el usuario complete
    ];

    // Convertir a CSV (formato simple)
    const csv = plantilla.map(row => row.join(',')).join('\n');
    
    // Crear blob y descargar
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'plantilla_inventario.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log('✅ Plantilla de inventario descargada');
}

/**
 * Maneja la selección del archivo Excel de inventario
 */
function subirArchivoInventario(input) {
    const file = input.files[0];
    
    if (!file) {
        archivoExcelInventarioSeleccionado = null;
        document.getElementById('excel-file-name-inventory').textContent = 'Ningún archivo seleccionado';
        document.getElementById('btn-procesar-excel-inventory').disabled = true;
        return;
    }

    // Validar extensión
    const extension = file.name.split('.').pop().toLowerCase();
    if (!['xlsx', 'xls', 'csv'].includes(extension)) {
        alert('❌ Por favor seleccione un archivo Excel válido (.xlsx, .xls o .csv)');
        input.value = '';
        archivoExcelInventarioSeleccionado = null;
        document.getElementById('excel-file-name-inventory').textContent = 'Ningún archivo seleccionado';
        document.getElementById('btn-procesar-excel-inventory').disabled = true;
        return;
    }

    // Validar tamaño (máx 5MB)
    if (file.size > 5 * 1024 * 1024) {
        alert('❌ El archivo es demasiado grande. Tamaño máximo: 5MB');
        input.value = '';
        archivoExcelInventarioSeleccionado = null;
        document.getElementById('excel-file-name-inventory').textContent = 'Ningún archivo seleccionado';
        document.getElementById('btn-procesar-excel-inventory').disabled = true;
        return;
    }

    archivoExcelInventarioSeleccionado = file;
    document.getElementById('excel-file-name-inventory').textContent = file.name;
    document.getElementById('btn-procesar-excel-inventory').disabled = false;
    
    console.log('✅ Archivo seleccionado:', file.name);
}

/**
 * Procesa e importa el archivo de inventario
 */
async function procesarArchivoInventario() {
    if (!archivoExcelInventarioSeleccionado) {
        alert('❌ Por favor seleccione un archivo primero');
        return;
    }

    const btnProcesar = document.getElementById('btn-procesar-excel-inventory');
    const textoOriginal = btnProcesar.innerHTML;
    
    btnProcesar.disabled = true;
    btnProcesar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';

    try {
        // Leer el archivo como texto (para CSV)
        const texto = await leerArchivoComoTexto(archivoExcelInventarioSeleccionado);
        
        // Parsear CSV
        const lineas = texto.split('\n').filter(linea => linea.trim());
        
        if (lineas.length < 2) {
            throw new Error('El archivo está vacío o no tiene datos válidos');
        }

        // Saltar la primera línea (encabezados)
        const itemsImportados = [];
        
        for (let i = 1; i < lineas.length; i++) {
            const campos = lineas[i].split(',').map(c => c.trim());
            
            if (campos.length >= 7 && campos[0] && campos[1]) {
                itemsImportados.push({
                    tipo: campos[0],
                    nombre: campos[1],
                    modelo: campos[2],
                    codigo: campos[3],
                    precio: campos[4],
                    detalle: campos[5],
                    cantidad: campos[6]
                });
            }
        }

        if (itemsImportados.length === 0) {
            throw new Error('No se encontraron productos/servicios válidos en el archivo');
        }

        // Aquí iría la llamada al backend para guardar múltiples items
        console.log('Items a importar:', itemsImportados);
        
        alert(`✅ Se importaron ${itemsImportados.length} productos/servicios exitosamente`);
        
        // Limpiar
        document.getElementById('excel-upload-inventory').value = '';
        archivoExcelInventarioSeleccionado = null;
        document.getElementById('excel-file-name-inventory').textContent = 'Ningún archivo seleccionado';
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
