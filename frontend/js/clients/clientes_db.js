const CLIENTES_API_URL = `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.CLIENTES}`;
const TIPOS_ID_API_URL = `${CONFIG.API_BASE_URL}/api/tipos-identificacion`;

/**
 * Carga los tipos de identificación desde la base de datos
 */
async function cargarTiposIdentificacion() {
    try {
        const response = await fetch(TIPOS_ID_API_URL);
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('cliente-tipo-cedula');
            
            // Limpiar opciones existentes excepto la primera
            select.innerHTML = '<option value="">Tipo de Cédula</option>';
            
            // Agregar opciones desde la BD
            data.tipos.forEach(tipo => {
                const option = document.createElement('option');
                option.value = tipo.codigo;
                option.textContent = `${tipo.descripcion}`;
                select.appendChild(option);
            });
            
            console.log(`✅ Cargados ${data.count} tipos de identificación`);
        } else {
            console.error('Error al cargar tipos de identificación:', data.message);
        }
        
    } catch (error) {
        console.error('Error al cargar tipos de identificación:', error);
    }
}

/**
 * Guarda un cliente en la base de datos
 */
async function guardarClienteEnBD() {
    console.log('📝 Iniciando guardado de cliente...');
    
    try {
        // Obtener datos del formulario
        const cliente = {
            nombre: document.getElementById('cliente-nombre')?.value,
            tipo_cedula: document.getElementById('cliente-tipo-cedula')?.value,
            cedula: document.getElementById('cliente-cedula')?.value,
            telefono: document.getElementById('cliente-telefono')?.value,
            email: document.getElementById('cliente-email')?.value,
            direccion: document.getElementById('cliente-direccion')?.value
        };
        
        console.log('📦 Datos capturados del formulario:', cliente);
        
        // Validar datos requeridos
        if (!cliente.nombre || !cliente.cedula) {
            console.warn('⚠️ Validación fallida: Faltan campos requeridos');
            mostrarNotificacion('Por favor complete los campos requeridos (Nombre y Cédula)', 'error');
            return false;
        }
        
        if (!cliente.tipo_cedula) {
            console.warn('⚠️ Validación fallida: Falta tipo de cédula');
            mostrarNotificacion('Por favor seleccione el tipo de cédula', 'error');
            return false;
        }
        
        console.log('✅ Validación exitosa, enviando a la API...');
        
        // Enviar a la API
        const response = await fetch(CLIENTES_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(cliente)
        });
        
        console.log('📡 Respuesta recibida, status:', response.status);
        
        const data = await response.json();
        console.log('📄 Datos de respuesta:', data);
        
        if (data.success) {
            console.log('✅ Cliente guardado exitosamente con ID:', data.cliente_id);
            mostrarNotificacion('✅ Cliente guardado exitosamente en la base de datos', 'success');
            limpiarFormularioCliente();
            cargarListaClientes(); // Recargar lista
            return true;
        } else {
            console.error('❌ Error del servidor:', data.message);
            mostrarNotificacion(`❌ Error: ${data.message}`, 'error');
            return false;
        }
        
    } catch (error) {
        console.error('❌ Error al guardar cliente:', error);
        console.error('   Detalles:', error.message);
        mostrarNotificacion('❌ Error de conexión con la base de datos', 'error');
        return false;
    }
}

/**
 * Carga la lista de clientes desde la base de datos
 */
async function cargarListaClientes() {
    try {
        const response = await fetch(CLIENTES_API_URL);
        const data = await response.json();
        
        if (data.success) {
            mostrarClientesEnLista(data.clientes);
            console.log(`✅ Cargados ${data.count} clientes desde la BD`);
        } else {
            console.error('Error al cargar clientes:', data.message);
        }
        
    } catch (error) {
        console.error('Error al cargar clientes:', error);
    }
}

/**
 * Muestra los clientes en la lista
 */
function mostrarClientesEnLista(clientes) {
    const container = document.querySelector('.card-list-container');
    
    if (!container) {
        console.warn('Contenedor de lista no encontrado');
        return;
    }
    
    if (clientes.length === 0) {
        container.innerHTML = `
            <div class="no-items-message">
                <i class="fas fa-users"></i>
                <p>No hay clientes registrados</p>
                <p class="hint">Agrega tu primer cliente</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = clientes.map(cliente => `
        <div class="client-card" data-cliente-id="${cliente.cliente_id}">
            <h4>${cliente.nombre}</h4>
            <p>Cédula: ${cliente.cedula}</p>
            <p>Teléfono: ${cliente.telefono || 'N/A'}</p>
            <p>Email: ${cliente.email || 'N/A'}</p>
            <p>Dirección: ${cliente.direccion || 'N/A'}</p>
            <div class="action-icon" title="Editar" data-tooltip="Editar Cliente" onclick="editarCliente(${cliente.cliente_id})">
                <i class="fas fa-pen"></i>
            </div>
            <div class="action-icon delete-icon" title="Eliminar" data-tooltip="Eliminar Cliente" onclick="eliminarCliente(${cliente.cliente_id})">
                <i class="fas fa-trash"></i>
            </div>
        </div>
    `).join('');
}

/**
 * Edita un cliente (carga datos en el formulario)
 */
async function editarCliente(clienteId) {
    try {
        const response = await fetch(`${CLIENTES_API_URL}/${clienteId}`);
        const data = await response.json();
        
        if (data.success) {
            const cliente = data.cliente;
            
            // Cargar datos en el formulario
            document.getElementById('cliente-nombre').value = cliente.nombre;
            document.getElementById('cliente-tipo-cedula').value = cliente.tipo_cedula;
            document.getElementById('cliente-cedula').value = cliente.cedula;
            document.getElementById('cliente-telefono').value = cliente.telefono || '';
            document.getElementById('cliente-email').value = cliente.email || '';
            document.getElementById('cliente-direccion').value = cliente.direccion || '';
            
            // Scroll al formulario
            document.querySelector('.client-form-container').scrollIntoView({ behavior: 'smooth' });
            
            mostrarNotificacion('📝 Cliente cargado para edición', 'info');
        }
        
    } catch (error) {
        console.error('Error al cargar cliente:', error);
        mostrarNotificacion('❌ Error al cargar cliente', 'error');
    }
}

/**
 * Elimina un cliente de la base de datos
 */
async function eliminarCliente(clienteId) {
    if (!confirm('¿Está seguro de que desea eliminar este cliente?')) {
        return;
    }
    
    try {
        const response = await fetch(`${CLIENTES_API_URL}/${clienteId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Cliente eliminado exitosamente', 'success');
            cargarListaClientes(); // Recargar lista
        } else {
            mostrarNotificacion(`❌ Error: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error('Error al eliminar cliente:', error);
        mostrarNotificacion('❌ Error de conexión', 'error');
    }
}

/**
 * Busca clientes en la base de datos
 */
async function buscarClientesEnBD(query) {
    try {
        mostrarCargandoLista();
        
        const response = await fetch(`${CLIENTES_API_URL}/buscar?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarClientesEnLista(data.clientes);
            console.log(`🔍 Encontrados ${data.count} clientes`);
        } else {
            mostrarClientesEnLista([]);
        }
        
    } catch (error) {
        console.error('Error en búsqueda:', error);
        mostrarNotificacion('❌ Error al buscar clientes', 'error');
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
 * Limpia el formulario de cliente
 */
function limpiarFormularioCliente() {
    document.getElementById('cliente-nombre').value = '';
    document.getElementById('cliente-tipo-cedula').value = '';
    document.getElementById('cliente-cedula').value = '';
    document.getElementById('cliente-telefono').value = '';
    document.getElementById('cliente-email').value = '';
    document.getElementById('cliente-direccion').value = '';
}

/**
 * Muestra notificación al usuario
 */
function mostrarNotificacion(mensaje, tipo = 'info') {
    const notif = document.createElement('div');
    notif.className = `notificacion notif-${tipo}`;
    notif.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check-circle' : tipo === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${mensaje}</span>
    `;
    
    document.body.appendChild(notif);
    
    setTimeout(() => notif.classList.add('show'), 10);
    
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

/**
 * Verifica conexión con la API
 */
async function verificarConexionClientesAPI() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.HEALTH}`);
        const data = await response.json();
        
        if (data.status === 'ok' && data.database === 'connected') {
            console.log('✅ Conexión con API de Clientes OK');
            return true;
        } else {
            console.warn('⚠️ Base de datos no conectada');
            return false;
        }
    } catch (error) {
        console.error('❌ Error de conexión con API de Clientes:', error);
        return false;
    }
}

/**
 * Configura el buscador de clientes con búsqueda en tiempo real
 */
function configurarBuscadorClientes() {
    const inputBusqueda = document.querySelector('.client-list-container .search-input input');
    const btnBusqueda = document.querySelector('.client-list-container .search-input button');
    
    if (!inputBusqueda) return;
    
    let timeoutId;
    
    // Búsqueda en tiempo real mientras escribe
    inputBusqueda.addEventListener('input', (e) => {
        clearTimeout(timeoutId);
        const query = e.target.value.trim();
        
        if (query.length === 0) {
            cargarListaClientes();
            return;
        }
        
        if (query.length < 2) {
            return;
        }
        
        timeoutId = setTimeout(() => {
            buscarClientesEnBD(query);
        }, 300);
    });
    
    // Búsqueda al hacer click en el botón
    if (btnBusqueda) {
        btnBusqueda.addEventListener('click', (e) => {
            e.preventDefault();
            const query = inputBusqueda.value.trim();
            if (query) {
                buscarClientesEnBD(query);
            } else {
                cargarListaClientes();
            }
        });
    }
    
    // Búsqueda al presionar Enter
    inputBusqueda.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = inputBusqueda.value.trim();
            if (query) {
                buscarClientesEnBD(query);
            } else {
                cargarListaClientes();
            }
        }
    });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🔧 Inicializando módulo de clientes...');
    
    // Verificar conexión
    const conectado = await verificarConexionClientesAPI();
    
    if (conectado) {
        console.log('✅ Conexión establecida, cargando catálogos...');
        
        // Cargar tipos de identificación
        await cargarTiposIdentificacion();
        
        // Cargar lista de clientes
        cargarListaClientes();
        
        // Configurar buscador en tiempo real
        configurarBuscadorClientes();
        
        console.log('✅ Módulo de clientes inicializado correctamente');
    } else {
        console.warn('❌ Modo Offline: No se pudo conectar con el servidor de clientes.');
    }
});
