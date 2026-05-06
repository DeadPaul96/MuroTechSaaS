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
            if (this.dataset.tab === 'empresa') cargarDatosEmpresa();
            if (this.dataset.tab === 'facturacion') cargarDatosFacturacion();
        });
    });

    // --- USUARIOS ---
    async function cargarUsuarios() {
        try {
            const res = await fetch(`${CONFIG.API_BASE_URL}/api/usuarios`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) return;
            const usuarios = await res.json();
            const tbody = document.getElementById('lista-usuarios');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            usuarios.forEach(u => {
                const tr = document.createElement('tr');
                const rol = u.rol || 'Usuario';
                const rolClass = rol === 'Administrador' ? 'role-admin' : (rol === 'Auditor' ? 'role-viewer' : 'role-user');
                
                tr.innerHTML = `
                    <td>${u.nombre} ${u.is_superadmin ? '<i class="fas fa-crown" style="color:gold; font-size:0.7rem;"></i>' : ''}</td>
                    <td>${u.email}</td>
                    <td><span class="role-badge ${rolClass}">${rol}</span></td>
                    <td><span style="color:${u.activo ? '#15803d' : '#ef4444'}; font-weight:700; font-size:0.82rem;">● ${u.activo ? 'Activo' : 'Inactivo'}</span></td>
                    <td>
                        <button class="btn-action edit" onclick="editarUsuario(${u.id})"><i class="fas fa-edit"></i></button>
                        ${u.is_superadmin ? '' : `<button class="btn-action del" onclick="eliminarUsuario(${u.id})"><i class="fas fa-trash-alt"></i></button>`}
                    </td>
                `;
                tbody.appendChild(tr);
            });
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
            const res = await fetch(`${CONFIG.API_BASE_URL}/api/usuarios`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ nombre, email, password: pass, rol, pantallas })
            });
            if (res.ok) {
                Swal.fire({icon:'success',title:'Usuario creado',timer:1500,showConfirmButton:false});
                cargarUsuarios();
            }
        } catch (err) { console.error(err); }
    });

    window.eliminarUsuario = async function(id) {
        if ((await Swal.fire({title:'¿Eliminar?', icon:'warning', showCancelButton:true})).isConfirmed) {
            await fetch(`${CONFIG.API_BASE_URL}/api/usuarios/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            cargarUsuarios();
        }
    };

    // --- EMPRESA ---
    async function cargarDatosEmpresa() {
        try {
            const res = await fetch(`${CONFIG.API_BASE_URL}/api/config/empresa`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('emp-razon').value = data.razon_social || '';
                document.getElementById('emp-comercial').value = data.nombre_comercial || '';
                document.getElementById('emp-cedula').value = data.cedula_juridica || '';
                document.getElementById('emp-actividad').value = data.actividad_economica || '';
                document.getElementById('emp-correo').value = data.correo_hacienda || '';
                document.getElementById('emp-telefono').value = data.telefono || '';
                document.getElementById('emp-direccion').value = data.direccion || '';
            }
        } catch (err) { console.error(err); }
    }

    document.getElementById('btn-guardar-empresa')?.addEventListener('click', async function(){
        const payload = {
            razon_social: document.getElementById('emp-razon').value,
            nombre_comercial: document.getElementById('emp-comercial').value,
            cedula_juridica: document.getElementById('emp-cedula').value,
            actividad_economica: document.getElementById('emp-actividad').value,
            correo_hacienda: document.getElementById('emp-correo').value,
            telefono: document.getElementById('emp-telefono').value,
            direccion: document.getElementById('emp-direccion').value
        };

        const res = await fetch(`${CONFIG.API_BASE_URL}/api/config/empresa`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        if (res.ok) Swal.fire('Éxito', 'Datos de empresa actualizados', 'success');
    });

    // --- FACTURACIÓN ---
    async function cargarDatosFacturacion() {
        try {
            const res = await fetch(`${CONFIG.API_BASE_URL}/api/config/facturacion`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('api-user').value = data.api_user || '';
                document.getElementById('api-sucursal').value = data.sucursal_num || '001';
                document.getElementById('api-terminal').value = data.terminal_num || '00001';
                document.getElementById('api-ambiente').value = data.ambiente || 'stag';
            }
        } catch (err) { console.error(err); }
    }

    document.getElementById('btn-guardar-api')?.addEventListener('click', async function(){
        const payload = {
            api_user: document.getElementById('api-user').value,
            api_pass: document.getElementById('api-pass').value, // Solo si se cambia
            sucursal_num: document.getElementById('api-sucursal').value,
            terminal_num: document.getElementById('api-terminal').value,
            ambiente: document.getElementById('api-ambiente').value
        };

        const res = await fetch(`${CONFIG.API_BASE_URL}/api/config/facturacion`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        if (res.ok) Swal.fire('Éxito', 'Configuración de facturación actualizada', 'success');
    });

    // Inicialización
    cargarUsuarios();

})();

// Partículas
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