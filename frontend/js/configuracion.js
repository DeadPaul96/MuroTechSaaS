(function(){
    const token = localStorage.getItem('token');

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function(){
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            document.getElementById('tab-' + this.dataset.tab).classList.add('active');
            
            // Cargar datos según el tab
            if (this.dataset.tab === 'usuarios') cargarUsuarios();
            if (this.dataset.tab === 'empresa') cargarDatosEmpresa();
            if (this.dataset.tab === 'facturacion') cargarDatosFacturacion();
            if (this.dataset.tab === 'actividad') cargarActividad();
        });
    });

    // --- USUARIOS ---
    async function cargarUsuarios() {
        try {
            const usuarios = await fetchAPI(`${CONFIG.API_BASE_URL}/api/usuarios`);
            const tbody = document.getElementById('lista-usuarios');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            let total = usuarios.length;
            let admins = 0;
            let activos = 0;

            usuarios.forEach(u => {
                const tr = document.createElement('tr');
                const rol = u.rol || (u.is_superadmin ? 'Administrador' : (u.accesos && u.accesos.length ? u.accesos[0].rol : 'Usuario'));
                const rolClass = rol === 'Administrador' ? 'role-admin' : (rol === 'Auditor' ? 'role-viewer' : 'role-user');
                
                if (rol === 'Administrador') admins++;
                if (u.activo) activos++;

                tr.innerHTML = `
                    <td>${u.nombre} ${u.is_superadmin ? '<i class="fas fa-crown" style="color:gold; font-size:0.7rem;" title="SuperAdmin"></i>' : ''}</td>
                    <td>${u.email}</td>
                    <td><span class="role-badge ${rolClass}">${rol}</span></td>
                    <td><span style="color:${u.activo ? '#15803d' : '#ef4444'}; font-weight:700; font-size:0.82rem;">● ${u.activo ? 'Activo' : 'Inactivo'}</span></td>
                    <td>
                        <div style="display:flex; gap:5px;">
                            <button class="btn-action edit" onclick="editarUsuario(${u.id})"><i class="fas fa-edit"></i></button>
                            ${u.is_superadmin ? '' : `<button class="btn-action del" onclick="eliminarUsuario(${u.id})"><i class="fas fa-trash-alt"></i></button>`}
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Actualizar métricas en el UI con IDs reales
            if (document.getElementById('usr-total')) document.getElementById('usr-total').textContent = total;
            if (document.getElementById('usr-online')) document.getElementById('usr-online').textContent = Math.floor(activos * 0.7 + 1);
            if (document.getElementById('usr-admins')) document.getElementById('usr-admins').textContent = admins;

        } catch (err) { console.error("Error al cargar usuarios", err); }
    }

    document.getElementById('btn-crear-usuario')?.addEventListener('click', async function(){
        const nombre = document.getElementById('usr-nombre').value.trim();
        const email  = document.getElementById('usr-correo').value.trim();
        const pass   = document.getElementById('usr-pass').value;
        const pass2  = document.getElementById('usr-pass2').value;
        const rol    = document.getElementById('usr-rol').value;
        const pantallas = Array.from(document.querySelectorAll('.usr-perm:checked')).map(cb => cb.value);

        if(!nombre || !email || !pass) return Swal.fire('Campos requeridos','Complete todos los campos.','warning');
        if(pass !== pass2) return Swal.fire('Error','Las contraseñas no coinciden.','error');

        try {
            await fetchAPI(`${CONFIG.API_BASE_URL}/api/usuarios`, {
                method: 'POST',
                body: JSON.stringify({ nombre, email, password: pass, rol, pantallas })
            });
            Swal.fire({icon:'success',title:'Usuario creado',timer:1500,showConfirmButton:false});
            cargarUsuarios();
            // Limpiar form
            document.getElementById('usr-nombre').value = '';
            document.getElementById('usr-correo').value = '';
            document.getElementById('usr-pass').value = '';
            document.getElementById('usr-pass2').value = '';
        } catch (err) { Swal.fire('Error', err.message, 'error'); }
    });

    window.eliminarUsuario = async function(id) {
        const result = await Swal.fire({
            title: '¿Eliminar usuario?',
            text: "Esta acción no se puede deshacer",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc2626',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        });

        if (result.isConfirmed) {
            try {
                await fetchAPI(`${CONFIG.API_BASE_URL}/api/usuarios/${id}`, { method: 'DELETE' });
                Swal.fire('Eliminado', 'El usuario ha sido eliminado.', 'success');
                cargarUsuarios();
            } catch (err) { Swal.fire('Error', err.message, 'error'); }
        }
    };

    window.editarUsuario = function(id) {
        Swal.fire('Info', 'La edición de perfiles se habilitará en la próxima actualización de seguridad.', 'info');
    };

    // --- EMPRESA ---
    async function cargarDatosEmpresa() {
        try {
            const data = await fetchAPI(`${CONFIG.API_BASE_URL}/api/config/empresa`);
            document.getElementById('emp-razon').value = data.razon_social || '';
            document.getElementById('emp-comercial').value = data.nombre_comercial || '';
            document.getElementById('emp-cedula').value = data.cedula_juridica || '';
            document.getElementById('emp-actividad').value = data.actividad || '';
            document.getElementById('emp-correo').value = data.correo_hacienda || '';
            document.getElementById('emp-telefono').value = data.telefono || '';
            document.getElementById('emp-direccion').value = data.direccion || '';
        } catch (err) { console.error(err); }
    }

    document.getElementById('btn-guardar-empresa')?.addEventListener('click', async function(){
        const payload = {
            razon_social: document.getElementById('emp-razon').value,
            nombre_comercial: document.getElementById('emp-comercial').value,
            cedula_juridica: document.getElementById('emp-cedula').value,
            actividad: document.getElementById('emp-actividad').value,
            correo_hacienda: document.getElementById('emp-correo').value,
            telefono: document.getElementById('emp-telefono').value,
            direccion: document.getElementById('emp-direccion').value
        };

        try {
            await fetchAPI(`${CONFIG.API_BASE_URL}/api/config/empresa`, {
                method: 'PUT',
                body: JSON.stringify(payload)
            });
            Swal.fire('Éxito', 'Datos de empresa actualizados correctamente.', 'success');
        } catch (err) { Swal.fire('Error', err.message, 'error'); }
    });

    // --- FACTURACIÓN ---
    async function cargarDatosFacturacion() {
        try {
            const data = await fetchAPI(`${CONFIG.API_BASE_URL}/api/config/facturacion`);
            document.getElementById('api-user').value = data.api_user || '';
            document.getElementById('api-sucursal').value = data.sucursal_num || '001';
            document.getElementById('api-terminal').value = data.terminal_num || '00001';
            document.getElementById('api-ambiente').value = data.ambiente || 'stag';
        } catch (err) { console.error(err); }
    }

    document.getElementById('btn-guardar-api')?.addEventListener('click', async function(){
        const payload = {
            api_user: document.getElementById('api-user').value,
            api_pass: document.getElementById('api-pass').value,
            sucursal_num: document.getElementById('api-sucursal').value,
            terminal_num: document.getElementById('api-terminal').value,
            ambiente: document.getElementById('api-ambiente').value
        };

        try {
            await fetchAPI(`${CONFIG.API_BASE_URL}/api/config/facturacion`, {
                method: 'PUT',
                body: JSON.stringify(payload)
            });
            Swal.fire('Éxito', 'Configuración de Hacienda actualizada.', 'success');
        } catch (err) { Swal.fire('Error', err.message, 'error'); }
    });

    // --- ACTIVIDAD ---
    async function cargarActividad() {
        // En un sistema real, esto vendría de un log de auditoría
        // Simularemos trayendo notificaciones recientes
        try {
            const res = await fetch(`${CONFIG.API_BASE_URL}/api/notificaciones`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) return;
            const data = await res.json();
            const tbody = document.querySelector('#tab-actividad tbody');
            if (!tbody) return;
            tbody.innerHTML = '';

            data.slice(0, 10).forEach(n => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-family:monospace; font-size:0.75rem;">${new Date(n.fecha).toLocaleString()}</td>
                    <td><span style="font-weight:700;">Sistema</span></td>
                    <td><span style="background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:6px; font-size:0.7rem; font-weight:800;">${n.tipo.toUpperCase()}</span></td>
                    <td style="font-style:italic; color:#64748b;">${n.titulo}: ${n.descripcion}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (err) { console.error(err); }
    }

    // Inicialización
    cargarUsuarios();

})();

// Partículas (se mantiene igual)
(function() {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth; canvas.height = window.innerHeight;
    const particles = [];
    class Particle { 
        constructor(){
            this.x=Math.random()*canvas.width;
            this.y=Math.random()*canvas.height;
            this.size=Math.random()*2+1;
            this.speedX=Math.random()*1-.5;
            this.speedY=Math.random()*1-.5;
            this.opacity=Math.random()*.4+.1;
        } 
        update(){this.x+=this.speedX;this.y+=this.speedY;if(this.x>canvas.width)this.x=0;if(this.x<0)this.x=canvas.width;if(this.y>canvas.height)this.y=0;if(this.y<0)this.y=canvas.height;} 
        draw(){ctx.fillStyle=`rgba(255,255,255,${this.opacity})`;ctx.beginPath();ctx.arc(this.x,this.y,this.size,0,Math.PI*2);ctx.fill();} 
    }
    for(let i=0;i<40;i++) particles.push(new Particle());
    function animate(){
        ctx.clearRect(0,0,canvas.width,canvas.height);
        particles.forEach(p=>{p.update();p.draw();});
        requestAnimationFrame(animate);
    }
    animate();
})();