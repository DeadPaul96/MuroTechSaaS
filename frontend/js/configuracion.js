(function(){
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function(){
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            document.getElementById('tab-' + this.dataset.tab).classList.add('active');
        });
    });

    // Crear usuario
    document.getElementById('btn-crear-usuario').addEventListener('click', function(){
        const nombre = document.getElementById('usr-nombre').value.trim();
        const correo = document.getElementById('usr-correo').value.trim();
        const pass   = document.getElementById('usr-pass').value;
        const pass2  = document.getElementById('usr-pass2').value;
        const rol    = document.getElementById('usr-rol').value;
        if(!nombre || !correo) return Swal.fire('Campos requeridos','Complete nombre y correo.','warning');
        if(pass !== pass2)     return Swal.fire('Error','Las contraseñas no coinciden.','error');
        const roles = {admin:'role-admin',user:'role-user',viewer:'role-viewer'};
        const labels = {admin:'Admin',user:'Usuario',viewer:'Lectura'};
        const tbody = document.getElementById('lista-usuarios');
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${nombre}</td><td>${correo}</td>
            <td><span class="role-badge ${roles[rol]}">${labels[rol]}</span></td>
            <td><span style="color:#15803d;font-weight:700;font-size:0.82rem;">● Activo</span></td>
            <td><button class="btn-action edit"><i class="fas fa-edit"></i></button>
                <button class="btn-action del" onclick="this.closest('tr').remove()"><i class="fas fa-trash-alt"></i></button></td>`;
        tbody.appendChild(tr);
        ['usr-nombre','usr-correo','usr-pass','usr-pass2'].forEach(id => document.getElementById(id).value='');
        Swal.fire({icon:'success',title:'Usuario creado',timer:1500,showConfirmButton:false});
    });

    // Guardar genérico
    ['btn-guardar-empresa','btn-guardar-api','btn-guardar-seguridad','btn-guardar-sistema'].forEach(id => {
        document.getElementById(id)?.addEventListener('click', () =>
            Swal.fire({icon:'success',title:'Guardado',text:'Configuración actualizada correctamente.',timer:1600,showConfirmButton:false}));
    });

    document.getElementById('btn-subir-p12')?.addEventListener('click', () =>
        Swal.fire({icon:'success',title:'Llave actualizada',text:'El certificado fue cargado correctamente.',timer:1600,showConfirmButton:false}));

    document.getElementById('btn-limpiar-cache')?.addEventListener('click', () =>
        Swal.fire({icon:'success',title:'Caché limpiado',text:'El sistema fue optimizado.',timer:1500,showConfirmButton:false}));

    document.getElementById('btn-reset-sistema')?.addEventListener('click', () =>
        Swal.fire({title:'¿Restablecer configuración?',text:'Esta acción no se puede deshacer.',icon:'warning',
            showCancelButton:true,confirmButtonColor:'#dc2626',cancelButtonText:'Cancelar',confirmButtonText:'Sí, restablecer'})
        .then(r => { if(r.isConfirmed) Swal.fire({icon:'success',title:'Restablecido',timer:1500,showConfirmButton:false}); }));
})();



    const canvas = document.getElementById('particles-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth; canvas.height = window.innerHeight;
    const particles = [];
    class Particle { constructor(){this.x=Math.random()*canvas.width;this.y=Math.random()*canvas.height;this.size=Math.random()*2+1;this.speedX=Math.random()*1.5-.75;this.speedY=Math.random()*1.5-.75;this.opacity=Math.random()*.5+.2;} update(){this.x+=this.speedX;this.y+=this.speedY;if(this.x>canvas.width)this.x=0;if(this.x<0)this.x=canvas.width;if(this.y>canvas.height)this.y=0;if(this.y<0)this.y=canvas.height;} draw(){ctx.fillStyle=`rgba(255,255,255,${this.opacity})`;ctx.beginPath();ctx.arc(this.x,this.y,this.size,0,Math.PI*2);ctx.fill();} }
    for(let i=0;i<60;i++) particles.push(new Particle());
    function animate(){ctx.clearRect(0,0,canvas.width,canvas.height);particles.forEach(p=>{p.update();p.draw();});particles.forEach((p1,i)=>{particles.slice(i+1).forEach(p2=>{const d=Math.hypot(p1.x-p2.x,p1.y-p2.y);if(d<150){ctx.strokeStyle=`rgba(255,255,255,${0.1*(1-d/150)})`;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(p1.x,p1.y);ctx.lineTo(p2.x,p2.y);ctx.stroke();}});});requestAnimationFrame(animate);}
    animate();
    window.addEventListener('resize',()=>{canvas.width=window.innerWidth;canvas.height=window.innerHeight;});