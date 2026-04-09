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

        // Toggle de contraseñas
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