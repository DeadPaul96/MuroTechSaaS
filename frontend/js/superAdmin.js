/**
 * Ojo de Dios - SuperAdmin MUROTECH Logic
 * Management and Orchestration of SaaS Entities
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initial Access Check
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    if (!user.is_superadmin) {
        Swal.fire({
            icon: 'error',
            title: 'Acceso Denegado',
            text: 'Solo los SuperAdministradores pueden acceder a esta plataforma de control supremo.',
            confirmButtonColor: '#ef4444',
            background: 'rgba(255, 255, 255, 0.95)',
            backdrop: `rgba(0,10,30,0.8)`
        }).then(() => {
            window.location.href = 'inicioSesion.html';
        });
        return;
    }

    // 2. Initialize Dashboard
    initSuperAdmin();
});

const API_BASE = CONFIG.API_BASE_URL + '/api';

/**
 * Main initialization
 */
async function initSuperAdmin() {
    console.log('👁️ Ojo de Dios activado - Inicializando SuperAdmin...');
    
    loadDashboardMetrics();
    loadEmpresas();
    loadUsuarios();
    loadRoles();
}

/**
 * Tab Switching Logic
 */
function switchTab(tabName) {
    // Buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.currentTarget.classList.add('active');
    
    // Content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

/**
 * Fetch and Render Global Metrics
 */
async function loadDashboardMetrics() {
    try {
        const response = await fetch(`${API_BASE}/supadmin/dashboard`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            animateValue('total-empresas', 0, data.metrics.total_empresas, 1000);
            animateValue('total-usuarios', 0, data.metrics.total_usuarios, 1000);
            animateValue('total-superadmins', 0, data.metrics.total_superadmins, 1000);
            animateValue('usuarios-activos', 0, data.metrics.usuarios_activos, 1000);
        }
    } catch (error) {
        console.error('Error cargando dashboard:', error);
    }
}

/**
 * Company Management
 */
async function loadEmpresas() {
    const tbody = document.getElementById('empresas-tbody');
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:40px;"><i class="fas fa-spinner fa-spin"></i> Cargando empresas...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/supadmin/empresas`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            renderEmpresas(data.empresas);
        }
    } catch (error) {
        console.error('Error cargando empresas:', error);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:40px; color:#ef4444;">Error de conexión con el núcleo.</td></tr>';
    }
}

function renderEmpresas(empresas) {
    const tbody = document.getElementById('empresas-tbody');
    if (!empresas || empresas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:40px;">No se encontraron empresas en el multiverso.</td></tr>';
        return;
    }
    
    tbody.innerHTML = empresas.map(e => `
        <tr>
            <td style="color: var(--primary); font-weight: 800;">${e.razon_social}</td>
            <td>${e.cedula_juridica}</td>
            <td>${e.email_contacto || 'N/A'}</td>
            <td><i class="fas fa-users"></i> ${e.usuarios_count}</td>
            <td><i class="fas fa-building"></i> ${e.sucursales_count}</td>
            <td><span class="status-badge ${e.is_active !== false ? 'active' : 'inactive'}">${e.is_active !== false ? 'Activa' : 'Inactiva'}</span></td>
            <td>
                <button class="btn-action btn-primary" onclick="verEmpresa('${e.id}')" title="Ver ADN Empresa">
                    <i class="fas fa-microscope"></i>
                </button>
                <button class="btn-action btn-danger" onclick="eliminarEmpresa('${e.id}', '${e.razon_social}')" title="Eliminar del Sistema">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

/**
 * User Management
 */
async function loadUsuarios() {
    const tbody = document.getElementById('usuarios-tbody');
    try {
        const response = await fetch(`${API_BASE}/supadmin/usuarios`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            renderUsuarios(data.usuarios);
        }
    } catch (error) {
        console.error('Error cargando usuarios:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:40px; color:#ef4444;">Error cargando registros de usuarios.</td></tr>';
    }
}

function renderUsuarios(usuarios) {
    const tbody = document.getElementById('usuarios-tbody');
    if (!usuarios || usuarios.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:40px;">Sin usuarios detectados.</td></tr>';
        return;
    }
    
    tbody.innerHTML = usuarios.map(u => `
        <tr>
            <td style="font-weight:800;">${u.nombre}</td>
            <td>${u.email}</td>
            <td><small>${u.empresa_nombre}</small></td>
            <td><span class="status-badge ${u.is_superadmin ? 'super' : 'active'}">${u.is_superadmin ? 'SuperAdmin' : 'Usuario'}</span></td>
            <td><span class="status-badge ${u.is_active ? 'active' : 'inactive'}">${u.is_active ? 'Activo' : 'Inactivo'}</span></td>
            <td>
                <button class="btn-action ${u.is_active ? 'btn-danger' : 'btn-success'}" onclick="${u.is_active ? 'desactivar' : 'activar'}Usuario('${u.id}', '${u.nombre}')" title="${u.is_active ? 'Congelar' : 'Reanimar'}">
                    <i class="fas fa-${u.is_active ? 'snowflake' : 'bolt'}"></i>
                </button>
                <button class="btn-action btn-primary" onclick="promoverUsuario('${u.id}', '${u.nombre}')" title="Ascender a SuperAdmin" ${u.is_superadmin ? 'disabled style="opacity:0.3"' : ''}>
                    <i class="fas fa-chevron-circle-up"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

/**
 * Role Management
 */
async function loadRoles() {
    try {
        const response = await fetch(`${API_BASE}/supadmin/roles`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.getElementById('roles-tbody');
            tbody.innerHTML = data.roles.map(r => `
                <tr>
                    <td style="font-weight:800; color: var(--primary);">${r.nombre}</td>
                    <td>${r.descripcion}</td>
                    <td><span class="status-badge active">${r.usuarios_count} Usuarios</span></td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error cargando roles:', error);
    }
}

/**
 * Actions: Empresa
 */
async function verEmpresa(id) {
    try {
        const response = await fetch(`${API_BASE}/supadmin/empresas/${id}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            Swal.fire({
                title: data.empresa.razon_social,
                html: `
                    <div style="text-align: left; font-size: 0.9rem;">
                        <p><b>Cédula:</b> ${data.empresa.cedula_juridica}</p>
                        <p><b>Email:</b> ${data.empresa.email_contacto}</p>
                        <p><b>Sucursales:</b> ${data.sucursales.length}</p>
                        <p><b>Usuarios:</b> ${data.usuarios.length}</p>
                    </div>
                `,
                icon: 'info',
                confirmButtonColor: varColor('--primary')
            });
        }
    } catch (error) {
        Swal.fire('Error', 'No se pudieron obtener los detalles', 'error');
    }
}

async function eliminarEmpresa(id, nombre) {
    const { value: confirmed } = await Swal.fire({
        title: '¿Eliminar Empresa?',
        text: `Esta acción borrará todos los datos de "${nombre}". Es irreversible.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        cancelButtonColor: '#64748b',
        confirmButtonText: 'Sí, borrar del sistema',
        cancelButtonText: 'Cancelar'
    });

    if (!confirmed) return;
    
    try {
        const response = await fetch(`${API_BASE}/supadmin/empresas/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            Swal.fire('Eliminado', 'La empresa ha sido purgada del sistema.', 'success');
            loadEmpresas();
            loadDashboardMetrics();
        } else {
            Swal.fire('Error', data.message || 'No se pudo eliminar la empresa', 'error');
        }
    } catch (error) {
        Swal.fire('Error', 'Fallo en la conexión galáctica', 'error');
    }
}

/**
 * Actions: Usuario
 */
async function activarUsuario(id, nombre) {
    try {
        const response = await fetch(`${API_BASE}/supadmin/usuarios/${id}/activar`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        if (data.success) {
            Swal.fire('Activado', `El usuario ${nombre} ha sido restaurado.`, 'success');
            loadUsuarios();
        }
    } catch (error) { console.error(error); }
}

async function desactivarUsuario(id, nombre) {
    const { value: confirmed } = await Swal.fire({
        title: '¿Desactivar Usuario?',
        text: `¿Seguro que desea congelar el acceso de ${nombre}?`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#ef4444'
    });

    if (!confirmed) return;

    try {
        const response = await fetch(`${API_BASE}/supadmin/usuarios/${id}/desactivar`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        if (data.success) {
            Swal.fire('Desactivado', 'Acceso restringido correctamente.', 'success');
            loadUsuarios();
        }
    } catch (error) { console.error(error); }
}

async function promoverUsuario(id, nombre) {
    const { value: confirmed } = await Swal.fire({
        title: '¿Ascender a SuperAdmin?',
        text: `Otorgarás control total sobre todo el SaaS a ${nombre}.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: varColor('--primary')
    });

    if (!confirmed) return;

    try {
        const response = await fetch(`${API_BASE}/supadmin/usuarios/${id}/promover`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        if (data.success) {
            Swal.fire('Ascendido', 'Nuevo SuperAdmin registrado en la red.', 'success');
            loadUsuarios();
            loadDashboardMetrics();
        }
    } catch (error) { console.error(error); }
}

/**
 * Utility: Animation and Helpers
 */
function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id);
    if (!obj) return;
    
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function varColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function irA(page) {
    window.location.href = page;
}

function cerrarSesion() {
    localStorage.clear();
    window.location.href = 'inicioSesion.html';
}
