(function () {
    /* ── Mensajes en memoria (desde API) ──────────────────── */
    let mensajes = [];

    async function loadMensajes() {
        try {
            showLoading(true);
            mensajes = await fetchAPI(`${CONFIG.API_BASE_URL}/api/mensajes-receptor`);
            renderTabla(mensajes);
            actualizarBadge();
        } catch (err) {
            console.error("Error cargando mensajes:", err);
            showError('Error al cargar mensajes: ' + err.message);
        } finally {
            showLoading(false);
        }
    }

    function actualizarBadge() {
        document.getElementById('total-mensajes-badge').innerHTML =
            `<i class="fas fa-envelope"></i> ${mensajes.length} Mensajes`;
    }

    function renderTabla(lista) {
        const tbody = document.getElementById('lista-mensajes');
        tbody.innerHTML = '';
        if (!lista.length) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:40px; color:#94a3b8;">No hay mensajes receptor registrados</td></tr>`;
            return;
        }
        lista.forEach((m) => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #f1f5f9';
            tr.style.transition = 'background 0.2s';
            tr.onmouseover = () => tr.style.background = '#f8fafc';
            tr.onmouseout = () => tr.style.background = '';

            const tipoLabel = tipoMensajeLabel(m.tipo_mensaje);
            const estadoBadge = estadoLabel(m.estado);
            const fecha = m.created_at ? new Date(m.created_at).toLocaleString('es-CR', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit'
            }) : '—';

            tr.innerHTML = `
                <td style="padding:16px 20px;">
                    <span style="font-weight:700; font-size:0.75rem; color:#1e293b; font-family:monospace; letter-spacing:0.5px;">${m.clave_comprobante}</span>
                </td>
                <td style="padding:16px 20px;">
                    <span style="font-size:0.75rem; font-weight:800; padding:4px 10px; border-radius:8px; ${tipoLabel.style}">${tipoLabel.text}</span>
                </td>
                <td style="padding:16px 20px;">
                    <span style="font-size:0.78rem; color:#475569;">${m.detalle_mensaje || '—'}</span>
                </td>
                <td style="padding:16px 20px;">
                    <span style="font-size:0.72rem; font-weight:800; padding:3px 10px; border-radius:20px; ${estadoBadge.style}">${estadoBadge.text}</span>
                </td>
                <td style="padding:16px 20px;">
                    <span style="font-size:0.75rem; color:#64748b; font-weight:600;">${fecha}</span>
                </td>
                <td style="padding:16px 20px; text-align:center;">
                    <div style="display:flex; justify-content:center; gap:6px;">
                        ${m.estado === 'generado' ? `
                            <button class="btn-action" onclick="aceptarMensaje('${m.id}')" title="Aceptar" style="width:32px; height:32px; border-radius:8px; border:none; background:#f0fdf4; color:#16a34a; cursor:pointer;"><i class="fas fa-check"></i></button>
                            <button class="btn-action" onclick="rechazarMensaje('${m.id}')" title="Rechazar" style="width:32px; height:32px; border-radius:8px; border:none; background:#fef2f2; color:#dc2626; cursor:pointer;"><i class="fas fa-times"></i></button>
                        ` : `<span style="font-size:0.65rem; color:#94a3b8;">—</span>`}
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    function tipoMensajeLabel(tipo) {
        const map = {
            '1': { text: 'Aceptar', style: 'background:#d1fae5; color:#065f46;' },
            '2': { text: 'Aceptar Parcial', style: 'background:#fef9c3; color:#92400e;' },
            '3': { text: 'Rechazar', style: 'background:#fee2e2; color:#dc2626;' },
            'aceptar': { text: 'Aceptar', style: 'background:#d1fae5; color:#065f46;' },
            'parcial': { text: 'Aceptar Parcial', style: 'background:#fef9c3; color:#92400e;' },
            'rechazar': { text: 'Rechazar', style: 'background:#fee2e2; color:#dc2626;' },
        };
        return map[tipo] || { text: tipo || '—', style: 'background:#f1f5f9; color:#64748b;' };
    }

    function estadoLabel(estado) {
        const map = {
            'generado': { text: 'Generado', style: 'background:#eff6ff; color:#1e40af; border:1px solid #bfdbfe;' },
            'aceptado': { text: 'Aceptado', style: 'background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0;' },
            'rechazado': { text: 'Rechazado', style: 'background:#fef2f2; color:#dc2626; border:1px solid #fecaca;' },
            'parcial': { text: 'Acept. Parcial', style: 'background:#fefce8; color:#a16207; border:1px solid #fef08a;' },
            'enviado': { text: 'Enviado MH', style: 'background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0;' },
            'error': { text: 'Error', style: 'background:#fef2f2; color:#dc2626; border:1px solid #fecaca;' },
        };
        return map[estado] || { text: estado || '—', style: 'background:#f1f5f9; color:#64748b;' };
    }

    /* ── Mostrar modal para crear mensaje ────────────────────────── */
    function mostrarModalMensaje(tipoDefault) {
        Swal.fire({
            title: 'Nuevo Mensaje Receptor',
            html: `
                <div style="display:flex; flex-direction:column; gap:12px; margin-top:15px; text-align:left;">
                    <div>
                        <label style="font-size:0.7rem; font-weight:800; color:#64748b; display:block; margin-bottom:4px;">Clave del Comprobante (50 dígitos)</label>
                        <input id="swal-clave" class="fi" placeholder="506280624003..." maxlength="50" style="width:100%; box-sizing:border-box;">
                    </div>
                    <div>
                        <label style="font-size:0.7rem; font-weight:800; color:#64748b; display:block; margin-bottom:4px;">Tipo de Mensaje</label>
                        <select id="swal-tipo" class="premium-select" style="width:100%;">
                            <option value="1" ${tipoDefault === '1' ? 'selected' : ''}>Aceptar (1)</option>
                            <option value="2" ${tipoDefault === '2' ? 'selected' : ''}>Aceptar Parcial (2)</option>
                            <option value="3" ${tipoDefault === '3' ? 'selected' : ''}>Rechazar (3)</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-size:0.7rem; font-weight:800; color:#64748b; display:block; margin-bottom:4px;">Detalle (opcional, máx. 80 caracteres)</label>
                        <textarea id="swal-detalle" class="fi" placeholder="Motivo o detalle adicional..." maxlength="80" style="width:100%; box-sizing:border-box; min-height:60px; resize:none;"></textarea>
                    </div>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'Generar Mensaje',
            cancelButtonText: 'Cancelar',
            width: '500px',
            preConfirm: () => {
                const clave = document.getElementById('swal-clave').value.trim();
                const tipo = document.getElementById('swal-tipo').value;
                const detalle = document.getElementById('swal-detalle').value.trim();

                if (!clave) {
                    Swal.showValidationMessage('La clave del comprobante es requerida');
                    return false;
                }
                if (clave.length !== 50) {
                    Swal.showValidationMessage('La clave debe tener exactamente 50 dígitos');
                    return false;
                }
                return { clave_comprobante: clave, tipo_mensaje: tipo, detalle_mensaje: detalle };
            }
        }).then(r => {
            if (r.isConfirmed && r.value) {
                crearMensaje(r.value);
            }
        });
    }

    async function crearMensaje(data) {
        try {
            const result = await fetchAPI(`${CONFIG.API_BASE_URL}/api/mensajes-receptor`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            Swal.fire({
                icon: 'success',
                title: 'Mensaje Receptor generado',
                text: `ID: ${result.id || 'OK'}`,
                timer: 2000,
                showConfirmButton: false
            });
            loadMensajes();
        } catch (err) {
            console.error("Error creando mensaje:", err);
            showError('Error al generar mensaje: ' + err.message);
        }
    }

    /* ── Acciones rápidas desde la tabla ─────────────────────────── */
    window.aceptarMensaje = function (id) {
        const msg = mensajes.find(m => m.id === id);
        if (!msg) return;
        Swal.fire({
            title: '¿Aceptar este comprobante?',
            text: `Clave: ${msg.clave_comprobante}`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#16a34a',
            confirmButtonText: 'Sí, Aceptar',
            cancelButtonText: 'Cancelar'
        }).then(r => {
            if (r.isConfirmed) {
                enviarMensajeAccion(id, '1');
            }
        });
    };

    window.rechazarMensaje = function (id) {
        const msg = mensajes.find(m => m.id === id);
        if (!msg) return;
        Swal.fire({
            title: '¿Rechazar este comprobante?',
            text: `Clave: ${msg.clave_comprobante}`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc2626',
            confirmButtonText: 'Sí, Rechazar',
            cancelButtonText: 'Cancelar'
        }).then(r => {
            if (r.isConfirmed) {
                enviarMensajeAccion(id, '3');
            }
        });
    };

    async function enviarMensajeAccion(id, tipo) {
        try {
            await fetchAPI(`${CONFIG.API_BASE_URL}/api/mensajes-receptor/${id}`, {
                method: 'PATCH',
                body: JSON.stringify({ tipo_mensaje: tipo, estado: tipo === '1' ? 'aceptado' : 'rechazado' })
            });
            Swal.fire({
                icon: 'success',
                title: tipo === '1' ? 'Comprobante aceptado' : 'Comprobante rechazado',
                timer: 1500,
                showConfirmButton: false
            });
            loadMensajes();
        } catch (err) {
            showError('Error al actualizar mensaje: ' + err.message);
        }
    }

    /* ── Filtro de búsqueda ─────────────────────────────────────── */
    document.getElementById('buscar-mensajes').addEventListener('input', function () {
        const q = this.value.trim().toLowerCase();
        if (!q) {
            renderTabla(mensajes);
            return;
        }
        const filtered = mensajes.filter(m =>
            (m.clave_comprobante && m.clave_comprobante.toLowerCase().includes(q)) ||
            (m.detalle_mensaje && m.detalle_mensaje.toLowerCase().includes(q)) ||
            (m.tipo_mensaje && m.tipo_mensaje.toLowerCase().includes(q))
        );
        renderTabla(filtered);
    });

    /* ── Eventos del formulario ──────────────────────────────────── */
    document.getElementById('addMensajeForm').addEventListener('submit', function (e) {
        e.preventDefault();
        const clave = document.getElementById('mr-clave').value.trim();
        const tipo = document.getElementById('mr-tipo').value;
        const detalle = document.getElementById('mr-detalle').value.trim();

        if (!clave || clave.length !== 50) {
            Swal.fire('Clave inválida', 'La clave del comprobante debe tener exactamente 50 dígitos.', 'warning');
            return;
        }

        crearMensaje({ clave_comprobante: clave, tipo_mensaje: tipo, detalle_mensaje: detalle });
        this.reset();
    });

    // Botones rápidos
    document.getElementById('btn-aceptar-rapido').addEventListener('click', function () {
        mostrarModalMensaje('1');
    });

    document.getElementById('btn-rechazar-rapido').addEventListener('click', function () {
        mostrarModalMensaje('3');
    });

    // Enter en clave → submit
    document.getElementById('mr-clave').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('addMensajeForm').requestSubmit();
        }
    });

    /* ── Renderizado Inicial ──────────────────────── */
    loadMensajes();

    /* ── Partículas animadas ──────────────────────── */
    const canvas = document.getElementById('particles-canvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        const particles = [];
        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 1;
                this.speedX = Math.random() * 1.5 - 0.75;
                this.speedY = Math.random() * 1.5 - 0.75;
                this.opacity = Math.random() * 0.5 + 0.2;
            }
            update() {
                this.x += this.speedX; this.y += this.speedY;
                if (this.x > canvas.width)  this.x = 0;
                if (this.x < 0)             this.x = canvas.width;
                if (this.y > canvas.height) this.y = 0;
                if (this.y < 0)             this.y = canvas.height;
            }
            draw() {
                ctx.fillStyle = `rgba(255,255,255,${this.opacity})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        for (let i = 0; i < 60; i++) particles.push(new Particle());
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => { p.update(); p.draw(); });
            particles.forEach((p1, index) => {
                particles.slice(index + 1).forEach(p2 => {
                    const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
                    if (dist < 150) {
                        ctx.strokeStyle = `rgba(255,255,255,${0.1 * (1 - dist / 150)})`;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(p1.x, p1.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.stroke();
                    }
                });
            });
            requestAnimationFrame(animate);
        }
        animate();
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
    }
})();
