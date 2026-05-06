document.addEventListener('DOMContentLoaded', () => {
        const btnConsultar = document.getElementById('btn-consultar-mh');
        const cedulaInput  = document.getElementById('cli-identificacion');
        const tipoIdSel    = document.getElementById('cli-tipo-id');
        const contactoSec  = document.getElementById('seccion-contacto-personal');

        // Lógica de visibilidad inteligente
        function toggleContacto() {
            const tipo = tipoIdSel.value;
            // Ocultamos 'Contacto Administrativo' (Nombres extras) en Física (01) y DIMEX (03)
            if (tipo === '01' || tipo === '03') {
                if (contactoSec) contactoSec.style.display = 'none';
            } else {
                if (contactoSec) contactoSec.style.display = 'block';
            }
        }
        tipoIdSel.addEventListener('change', toggleContacto);

        // MOTOR DE CONSULTA HACIENDA v4.4
        btnConsultar.onclick = async () => {
            const identificacion = cedulaInput.value.trim().replace(/\D/g, '');
            if (identificacion.length < 9) return Swal.fire('', 'Identificación inválida.', 'warning');

            const panelOk  = document.getElementById('mh-result-panel');
            const loading  = document.getElementById('mh-loading');

            panelOk.style.display  = 'none';
            loading.style.display  = 'block';

            try {
                const res = await fetch('https://api.hacienda.go.cr/fe/ae?identificacion=' + identificacion);
                loading.style.display = 'none';

                if (!res.ok) throw new Error();
                const d = await res.json();

                // 1. AUTO-SELECCIONAR TIPO DE ID DESDE HACIENDA
                if (d.tipoIdentificacion) {
                    tipoIdSel.value = d.tipoIdentificacion;
                }

                // 2. AUTO-COMPLETAR DATOS TRIBUTARIOS
                document.getElementById('cli-nombre').value = d.nombre || '';
                document.getElementById('cli-actividad').value = (d.actividades || [])[0]?.descripcion || '—';
                document.getElementById('cli-regimen').value = d.regimen ? d.regimen.descripcion : 'General';

                // 3. ACTUALIZAR PANEL VISUAL
                document.getElementById('mh-nombre-result').textContent = d.nombre;
                document.getElementById('mh-id-display').textContent = `CÓDIGO ${tipoIdSel.value} — ${identificacion}`;
                
                // 4. ACTUALIZAR VISIBILIDAD DE CONTACTO
                toggleContacto();

                panelOk.style.display = 'block';

            } catch (err) {
                loading.style.display = 'none';
                Swal.fire('Error', 'No se encontró en Hacienda.', 'error');
            }
        };

        // ... Lógica de Ubicaciones ...
        if (window.ubicacionData) {
            const provSel = document.getElementById('cli-provincia');
            const canSel  = document.getElementById('cli-canton');
            const disSel  = document.getElementById('cli-distrito');
            const barSel  = document.getElementById('cli-barrio');

            provSel.innerHTML = '<option value="" disabled selected>Provincia</option>';
            Object.keys(window.ubicacionData).forEach(p => {
                const o = document.createElement('option'); o.value = p; o.textContent = p; provSel.appendChild(o);
            });

            provSel.onchange = () => {
                canSel.innerHTML = '<option value="" disabled selected>Cantón</option>';
                Object.keys(window.ubicacionData[provSel.value]).forEach(c => {
                    const o = document.createElement('option'); o.value = c; o.textContent = c; canSel.appendChild(o);
                });
                disSel.innerHTML = ''; barSel.innerHTML = '';
            };
            canSel.onchange = () => {
                disSel.innerHTML = '<option value="" disabled selected>Distrito</option>';
                Object.keys(window.ubicacionData[provSel.value][canSel.value]).forEach(d => {
                    const o = document.createElement('option'); o.value = d; o.textContent = d; disSel.appendChild(o);
                });
                barSel.innerHTML = '';
            };
            disSel.onchange = () => {
                barSel.innerHTML = '<option value="" disabled selected>Barrio</option>';
                window.ubicacionData[provSel.value][canSel.value][disSel.value].forEach(b => {
                    const o = document.createElement('option'); o.value = b; o.textContent = b; barSel.appendChild(o);
                });
            };
        }

        // GESTIÓN DE LLAVE CRIPTOGRÁFICA
        const fileInput = document.getElementById('api_p12_file');
        const btnSelect = document.getElementById('btn-select-p12');
        const pinInput  = document.getElementById('api_pin');
        const metaInput = document.getElementById('api_p12_metadata');
        const fileName  = document.getElementById('p12-filename');

        btnSelect.onclick = () => fileInput.click();

        fileInput.onchange = () => {
            if (fileInput.files[0]) {
                fileName.textContent = `Archivo: ${fileInput.files[0].name}`;
                validarYExtraer();
            }
        };

        pinInput.oninput = () => {
            if (pinInput.value.length === 4) {
                validarYExtraer();
            }
        };

        async function validarYExtraer() {
            if (!fileInput.files[0] || pinInput.value.length < 4) return;

            const formData = new FormData();
            formData.append('api_p12_file', fileInput.files[0]);
            formData.append('api_pin', pinInput.value);

            try {
                const res = await fetch('/api/hacienda/validar-llave', {
                    method: 'POST',
                    body: formData
                });
                const d = await res.json();
                if (d.valid) {
                    metaInput.value = d.digits;
                    Swal.fire({
                        title: 'Llave Validada',
                        text: `Certificado de: ${d.subject}`,
                        icon: 'success',
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 3000
                    });
                } else {
                    metaInput.value = '';
                }
            } catch (err) {
                console.error('Error validando llave:', err);
            }
        }

        // ENVÍO FINAL DEL REGISTRO
        const form = document.getElementById('registroEmpresaForm');
        form.onsubmit = async (e) => {
            e.preventDefault();

            // Validaciones básicas
            const pass = document.getElementById('u-pass').value;
            const confirm = document.getElementById('u-pass-confirm').value;
            if (pass !== confirm) return Swal.fire('Error', 'Las contraseñas no coinciden.', 'error');

            const formData = new FormData();
            
            // Sección 1: Contribuyente
            formData.append('tipo_id', tipoIdSel.value);
            formData.append('identificacion', cedulaInput.value);
            formData.append('nombre', document.getElementById('cli-nombre').value);
            formData.append('actividad', document.getElementById('cli-actividad').value);
            formData.append('regimen', document.getElementById('cli-regimen').value);
            formData.append('telefono', document.getElementById('u-telefono').value);
            formData.append('email', document.getElementById('u-email').value);
            formData.append('direccion_completa', document.getElementById('cli-direccion').value);

            // Sección 2: Hacienda y P12
            formData.append('api_sucursal', document.getElementById('api-sucursal').value);
            formData.append('api_terminal', document.getElementById('api-terminal').value);
            formData.append('ultimo_consecutivo', document.getElementById('ultimo_numero_factura_mh').value);
            formData.append('api_usuario', form.querySelector('input[placeholder="Usuario API"]').value);
            formData.append('api_password', form.querySelector('input[placeholder="Contraseña API"]').value);
            formData.append('api_pin', pinInput.value);
            if (fileInput.files[0]) formData.append('api_p12_file', fileInput.files[0]);

            // Sección 3: Contacto Administrativo
            formData.append('contacto_nombre', form.querySelector('input[placeholder="Nombre"]').value);
            formData.append('contacto_apellidos', form.querySelector('input[placeholder="1er Apellido"]').value);
            formData.append('contacto_telefono', form.querySelector('input[placeholder="Teléfono del Contacto"]').value);
            formData.append('contacto_email', form.querySelector('input[placeholder="Correo del Contacto"]').value);

            // Sección 4: Credenciales Sistema
            formData.append('password', pass);
            formData.append('nombre_admin', document.getElementById('cli-nombre').value);

            Swal.fire({
                title: 'Procesando Registro...',
                html: 'Aplicando compresión y configurando bases de datos.',
                allowOutsideClick: false,
                didOpen: () => Swal.showLoading()
            });

            try {
                const res = await fetch('/api/contribuyentes', {
                    method: 'POST',
                    body: formData
                });
                const resData = await res.json();

                if (res.ok) {
                    Swal.fire('¡Éxito!', 'Registro completado. Bienvenido a MUROTECH.', 'success')
                        .then(() => window.location.href = 'inicioSesion.html');
                } else {
                    Swal.fire('Error', resData.message || 'No se pudo completar el registro.', 'error');
                }
            } catch (err) {
                Swal.fire('Error', 'Fallo de conexión con el servidor.', 'error');
            }
        };

        // Toggle de contraseñas (restante)
        document.querySelectorAll('.pass-toggle').forEach(btn => {
            btn.addEventListener('click', function() {
                const input = this.previousElementSibling;
                const icon = this.querySelector('i');
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.replace('fa-eye', 'fa-eye-slash');
                } else {
                    input.type = 'password';
                    icon.classList.replace('fa-eye-slash', 'fa-eye');
                }
            });
        });
    });

    // Partículas Animadas de Fondo (Idéntico a Login)
    const canvas = document.getElementById('particles-canvas');
    if(canvas) {
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles = [];
        const particleCount = 50;

        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 3 + 1;
                this.speedX = Math.random() * 2 - 1;
                this.speedY = Math.random() * 2 - 1;
                this.opacity = Math.random() * 0.5 + 0.2;
            }
            update() {
                this.x += this.speedX;
                this.y += this.speedY;
                if (this.x > canvas.width) this.x = 0;
                if (this.x < 0) this.x = canvas.width;
                if (this.y > canvas.height) this.y = 0;
                if (this.y < 0) this.y = canvas.height;
            }
            draw() {
                ctx.fillStyle = `rgba(255, 255, 255, ${this.opacity})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        for (let i = 0; i < particleCount; i++) {
            particles.push(new Particle());
        }

        function animateParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(particle => {
                particle.update();
                particle.draw();
            });
            particles.forEach((p1, index) => {
                particles.slice(index + 1).forEach(p2 => {
                    const distance = Math.hypot(p1.x - p2.x, p1.y - p2.y);
                    if (distance < 150) {
                        ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 * (1 - distance / 150)})`;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(p1.x, p1.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.stroke();
                    }
                });
            });
            requestAnimationFrame(animateParticles);
        }
        animateParticles();

        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
    }