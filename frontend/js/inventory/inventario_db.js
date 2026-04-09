// =============================================================
// CONEXIÓN CON BASE DE DATOS - INVENTARIO
// =============================================================

const INVENTARIO_API_URL = 'http://localhost:5001/api/inventario';

/**
 * Guarda un item en la base de datos
 */
async function guardarItemEnBD() {
    console.log('📝 Iniciando guardado de item...');
    
    try {
        // Obtener datos del formulario
        const item = {
            tipo_item: document.querySelector('select[name="tipo"]')?.value || 'Producto',
            nombre: document.getElementById('inv-nombre')?.value,
            codigo_interno: document.getElementById('inv-codigo')?.value,
            precio_unitario: parseFloat(document.getElementById('inv-precio')?.value) || 0,
            cabys_numero: document.getElementById('inv-cabys-numero')?.value,
            unidad_medida: document.querySelector('select[name="unidad"]')?.value,
            modelo_o_detalle: document.getElementById('inv-detalle')?.value,
            cantidad: parseInt(document.getElementById('inv-cantidad')?.value) || 0,
            url_imagen: document.getElementById('imagePreview')?.src || null
        };
        
        console.log('📦 Datos capturados del formulario:', item);
        
        // Validar datos requeridos
        if (!item.nombre || !item.precio_unitario) {
            console.warn('⚠️ Validación fallida: Faltan campos requeridos');
            console.log('   Nombre:', item.nombre);
            console.log('   Precio:', item.precio_unitario);
            mostrarNotificacion('Por favor complete los campos requeridos (Nombre y Precio)', 'error');
            return false;
        }
        
        console.log('✅ Validación exitosa, enviando a la API...');
        
        // Enviar a la API
        const response = await fetch(INVENTARIO_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(item)
        });
        
        console.log('📡 Respuesta recibida, status:', response.status);
        
        const data = await response.json();
        console.log('📄 Datos de respuesta:', data);
        
        if (data.success) {
            console.log('✅ Item guardado exitosamente con ID:', data.item_id);
            mostrarNotificacion('✅ Item guardado exitosamente en la base de datos', 'success');
            limpiarFormulario();
            cargarListaInventario(); // Recargar lista
            return true;
        } else {
            console.error('❌ Error del servidor:', data.message);
            mostrarNotificacion(`❌ Error: ${data.message}`, 'error');
            return false;
        }
        
    } catch (error) {
        console.error('❌ Error al guardar item:', error);
        console.error('   Detalles:', error.message);
        mostrarNotificacion('❌ Error de conexión con la base de datos', 'error');
        return false;
    }
}

/**
 * Carga la lista de items desde la base de datos
 */
async function cargarListaInventario() {
    try {
        const response = await fetch(INVENTARIO_API_URL);
        const data = await response.json();
        
        if (data.success) {
            mostrarItemsEnLista(data.items);
            console.log(`✅ Cargados ${data.count} items desde la BD`);
        } else {
            console.error('Error al cargar inventario:', data.message);
        }
        
    } catch (error) {
        console.error('Error al cargar inventario:', error);
    }
}

/**
 * Muestra los items en la lista
 */
function mostrarItemsEnLista(items) {
    const container = document.querySelector('.card-list-container');
    
    if (!container) {
        console.warn('Contenedor de lista no encontrado');
        return;
    }
    
    if (items.length === 0) {
        container.innerHTML = `
            <div class="no-items-message">
                <i class="fas fa-inbox"></i>
                <p>No hay items en el inventario</p>
                <p class="hint">Agrega tu primer producto o servicio</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = items.map(item => `
        <div class="client-card" data-item-id="${item.item_id}">
            <span class="item-type badge-${item.tipo_item.toLowerCase()}">${item.tipo_item}</span>
            <h4>${item.nombre}</h4>
            <p>Código: ${item.codigo_interno || 'N/A'}</p>
            <p>Precio: ₡${formatearPrecio(item.precio_unitario)}</p>
            ${item.cabys_numero ? `<p>CABYS: ${item.cabys_numero}</p>` : ''}
            ${item.modelo_o_detalle ? `<p>Detalle: ${item.modelo_o_detalle}</p>` : ''}
            <p>Cantidad: ${item.cantidad || 0} ${item.unidad_medida || 'unidades'}</p>
            <div class="action-icon" title="Editar" data-tooltip="Editar Item" onclick="editarItem(${item.item_id})">
                <i class="fas fa-pen"></i>
            </div>
            <div class="action-icon delete-icon" title="Eliminar" onclick="eliminarItem(${item.item_id})">
                <i class="fas fa-trash"></i>
            </div>
        </div>
    `).join('');
}

/**
 * Elimina un item de la base de datos
 */
async function eliminarItem(itemId) {
    if (!confirm('¿Está seguro de que desea eliminar este item?')) {
        return;
    }
    
    try {
        const response = await fetch(`${INVENTARIO_API_URL}/${itemId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Item eliminado exitosamente', 'success');
            cargarListaInventario(); // Recargar lista
        } else {
            mostrarNotificacion(`❌ Error: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error('Error al eliminar item:', error);
        mostrarNotificacion('❌ Error de conexión', 'error');
    }
}

/**
 * Edita un item (carga datos en el formulario)
 */
async function editarItem(itemId) {
    try {
        const response = await fetch(`${INVENTARIO_API_URL}/${itemId}`);
        const data = await response.json();
        
        if (data.success) {
            const item = data.item;
            
            // Cargar datos en el formulario
            document.querySelector('select[name="tipo"]').value = item.tipo_item;
            document.getElementById('inv-nombre').value = item.nombre;
            document.getElementById('inv-codigo').value = item.codigo_interno || '';
            document.getElementById('inv-precio').value = item.precio_unitario;
            document.getElementById('inv-cabys-numero').value = item.cabys_numero || '';
            document.querySelector('select[name="unidad"]').value = item.unidad_medida || '';
            document.getElementById('inv-detalle').value = item.modelo_o_detalle || '';
            document.getElementById('inv-cantidad').value = item.cantidad || 0;
            
            // Scroll al formulario
            document.querySelector('.add-item-form').scrollIntoView({ behavior: 'smooth' });
            
            mostrarNotificacion('📝 Item cargado para edición', 'info');
        }
        
    } catch (error) {
        console.error('Error al cargar item:', error);
        mostrarNotificacion('❌ Error al cargar item', 'error');
    }
}

/**
 * Busca items en la base de datos
 */
async function buscarItemsEnBD(query) {
    try {
        // Mostrar indicador de carga
        mostrarCargandoLista();
        
        const response = await fetch(`${INVENTARIO_API_URL}/buscar?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarItemsEnLista(data.items);
            
            // Mostrar mensaje de resultados
            const container = document.querySelector('.card-list-container');
            if (container && data.count > 0) {
                const mensaje = document.createElement('div');
                mensaje.className = 'search-results-info';
                mensaje.innerHTML = `<i class="fas fa-search"></i> ${data.count} resultado${data.count !== 1 ? 's' : ''} encontrado${data.count !== 1 ? 's' : ''} para "${query}"`;
                container.insertBefore(mensaje, container.firstChild);
                
                // Remover después de 3 segundos
                setTimeout(() => mensaje.remove(), 3000);
            }
            
            console.log(`🔍 Encontrados ${data.count} items`);
        } else {
            mostrarItemsEnLista([]);
        }
        
    } catch (error) {
        console.error('Error en búsqueda:', error);
        mostrarNotificacion('❌ Error al buscar items', 'error');
    }
}

/**
 * Muestra indicador de carga en la lista
 */
function mostrarCargandoLista() {
    const container = document.querySelector('.card-list-container');
    if (container) {
        container.innerHTML = `
            <div class="loading-message">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Buscando...</p>
            </div>
        `;
    }
}

/**
 * Limpia el formulario
 */
function limpiarFormulario() {
    document.querySelector('.add-item-form')?.reset();
    document.getElementById('imagePreview').style.display = 'none';
}

/**
 * Formatea precio con separadores de miles
 */
function formatearPrecio(precio) {
    return new Intl.NumberFormat('es-CR').format(precio);
}

/**
 * Muestra notificación al usuario
 */
function mostrarNotificacion(mensaje, tipo = 'info') {
    // Crear notificación
    const notif = document.createElement('div');
    notif.className = `notificacion notif-${tipo}`;
    notif.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check-circle' : tipo === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${mensaje}</span>
    `;
    
    document.body.appendChild(notif);
    
    // Mostrar
    setTimeout(() => notif.classList.add('show'), 10);
    
    // Ocultar después de 3 segundos
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

/**
 * Verifica conexión con la API
 */
async function verificarConexionBD() {
    try {
        const response = await fetch('http://localhost:5001/api/health');
        const data = await response.json();
        
        if (data.status === 'ok' && data.database === 'connected') {
            console.log('✅ Conexión con base de datos OK');
            return true;
        } else {
            console.warn('⚠️ Base de datos no conectada');
            return false;
        }
    } catch (error) {
        console.error('❌ Error de conexión con API:', error);
        return false;
    }
}

/**
 * Configura el buscador de inventario con búsqueda en tiempo real
 */
function configurarBuscadorInventario() {
    const inputBusqueda = document.querySelector('.client-list-container .search-input input');
    const btnBusqueda = document.querySelector('.client-list-container .search-input button');
    
    if (!inputBusqueda) return;
    
    let timeoutId;
    
    // Búsqueda en tiempo real mientras escribe
    inputBusqueda.addEventListener('input', (e) => {
        clearTimeout(timeoutId);
        const query = e.target.value.trim();
        
        if (query.length === 0) {
            // Si está vacío, mostrar todos
            cargarListaInventario();
            return;
        }
        
        if (query.length < 2) {
            // Esperar al menos 2 caracteres
            return;
        }
        
        // Debounce: esperar 300ms después de que deje de escribir
        timeoutId = setTimeout(() => {
            buscarItemsEnBD(query);
        }, 300);
    });
    
    // Búsqueda al hacer click en el botón
    if (btnBusqueda) {
        btnBusqueda.addEventListener('click', (e) => {
            e.preventDefault();
            const query = inputBusqueda.value.trim();
            if (query) {
                buscarItemsEnBD(query);
            } else {
                cargarListaInventario();
            }
        });
    }
    
    // Búsqueda al presionar Enter
    inputBusqueda.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = inputBusqueda.value.trim();
            if (query) {
                buscarItemsEnBD(query);
            } else {
                cargarListaInventario();
            }
        }
    });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🔧 Inicializando módulo de inventario...');
    
    // Verificar conexión
    const conectado = await verificarConexionBD();
    
    if (conectado) {
        console.log('✅ Conexión establecida, configurando componentes...');
        
        // Cargar lista de inventario
        cargarListaInventario();
        
        // Configurar buscador en tiempo real
        configurarBuscadorInventario();
        
        // Configurar formulario para prevenir submit por defecto
        const formulario = document.querySelector('.add-item-form');
        if (formulario) {
            formulario.addEventListener('submit', (e) => {
                e.preventDefault();
                console.log('📝 Formulario submit interceptado');
                guardarItemEnBD();
            });
            console.log('✅ Formulario configurado correctamente');
        }
        
        // Configurar botón de guardar (backup)
        const btnAgregar = document.querySelector('.add-item-btn');
        if (btnAgregar) {
            console.log('✅ Botón "Agregar Inventario" encontrado');
            btnAgregar.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔘 Botón "Agregar Inventario" clickeado');
                guardarItemEnBD();
            });
        }
        
        console.log('✅ Módulo de inventario inicializado correctamente');
    } else {
        console.error('❌ No se pudo conectar con la base de datos');
        mostrarNotificacion('⚠️ No se pudo conectar con la base de datos. Inicia el servidor de inventario.', 'error');
    }
});
