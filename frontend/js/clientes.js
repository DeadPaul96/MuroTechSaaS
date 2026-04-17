(function () {
        /* ── Clientes en memoria (desde MockDB) ──────────────────── */
        let clientes = window.muroDB ? window.muroDB.getClientes() : [];

        function actualizarBadge() {
            document.getElementById('total-clientes-badge').innerHTML = `<i class="fas fa-users-cog"></i> ${clientes.length} Clientes Registrados`;
        }

        function renderTabla(lista) {
            const tbody = document.getElementById('lista-clientes');
            tbody.innerHTML = '';
            if (!lista.length) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:40px; color:#94a3b8;">No hay clientes registrados</td></tr>`;
                return;
            }
            lista.forEach((c, idx) => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid #f1f5f9';
                tr.style.transition = 'background 0.2s';
                tr.onmouseover = () => tr.style.background = '#f8fafc';
                tr.onmouseout = () => tr.style.background = '';
                
                tr.innerHTML = `
                    <td style="padding:16px 20px; font-weight:800; font-size:0.82rem; color:#1e293b;">
                        <span style="font-size:0.6rem; background:#f1f5f9; padding:2px 6px; border-radius:4px; margin-right:6px; vertical-align:middle;">${c.tipoId}</span>
                        ${c.identificacion}
                    </td>
                    <td style="padding:16px 20px; font-weight:700; font-size:0.9rem; color:var(--primary-dark);">${c.nombre}</td>
                    <td style="padding:16px 20px; font-weight:600; color:#64748b;">${c.correo || '—'}</td>
                    <td style="padding:16px 20px; font-size:0.8rem; color:#94a3b8;">
                        <i class="fas fa-map-marker-alt" style="margin-right:4px; opacity:0.5;"></i> ${c.provincia || 'N/A'}, ${c.canton || 'N/A'}
                    </td>
                    <td style="padding:16px 20px; text-align:center; display:flex; justify-content:center; gap:8px;">
                        <button class="btn-action edit" onclick="editarCliente(${c.id})" style="width:34px; height:34px; border-radius:10px; border:none; background:#eff6ff; color:#3b82f6; cursor:pointer;"><i class="fas fa-edit"></i></button>
                        <button class="btn-action del" onclick="eliminarCliente(${c.id})" style="width:34px; height:34px; border-radius:10px; border:none; background:#fef2f2; color:#ef4444; cursor:pointer;"><i class="fas fa-trash-alt"></i></button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        window.editarCliente = function (id) {
            const cli = clientes.find(c => c.id === id);
            if (!cli) return;

            Swal.fire({
                title: 'Editar Contacto',
                html: `
                    <div style="display:flex; flex-direction:column; gap:10px; margin-top: 10px;">
                        <input id="swal-nombre" class="fi" value="${cli.nombre}" placeholder="Nombre / Razón Social" style="box-sizing:border-box;">
                        <input id="swal-correo" type="email" class="fi" value="${cli.correo || ''}" placeholder="Correo" style="box-sizing:border-box;">
                        <input id="swal-telefono" class="fi" value="${cli.telefono || ''}" placeholder="Teléfono" style="box-sizing:border-box;">
                        <input id="swal-direccion" class="fi" value="${cli.direccion || ''}" placeholder="Dirección Exacta" style="box-sizing:border-box;">
                    </div>
                `,
                showCancelButton: true,
                confirmButtonText: 'Guardar Cambios',
                cancelButtonText: 'Cancelar'
            }).then(r => {
                if (r.isConfirmed) {
                    const updatedData = {
                        nombre: document.getElementById('swal-nombre').value,
                        correo: document.getElementById('swal-correo').value,
                        telefono: document.getElementById('swal-telefono').value,
                        direccion: document.getElementById('swal-direccion').value
                    };
                    
                    window.muroDB.updateCliente(id, updatedData);
                    clientes = window.muroDB.getClientes();
                    renderTabla(clientes);
                    actualizarBadge();
                    Swal.fire('Guardado', 'Los datos del cliente han sido actualizados.', 'success');
                }
            });
        };

        window.eliminarCliente = function (id) {
            const cli = clientes.find(c => c.id === id);
            if (!cli) return;

            Swal.fire({
                title: '¿Eliminar cliente?',
                text: cli.nombre,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#ef4444',
                cancelButtonText: 'Cancelar',
                confirmButtonText: 'Sí, eliminar'
            }).then(r => {
                if (r.isConfirmed) {
                    window.muroDB.deleteCliente(id);
                    clientes = window.muroDB.getClientes();
                    renderTabla(clientes);
                    actualizarBadge();
                }
            });
        };

        /* ── Consulta API Hacienda (fe/ae) ───────────────────────────── */
        document.getElementById('btn-consultar-mh').addEventListener('click', async function () {
            const identificacion = document.getElementById('cli-identificacion').value.trim().replace(/\D/g, '');
            if (!identificacion || identificacion.length < 9) {
                Swal.fire('', 'Ingrese un número de identificación válido (mínimo 9 dígitos).', 'warning');
                return;
            }

            const panelOk  = document.getElementById('mh-result-panel');
            const panelErr = document.getElementById('mh-error-panel');
            const loading  = document.getElementById('mh-loading');

            panelOk.style.display  = 'none';
            panelErr.style.display = 'none';
            loading.style.display  = 'block';
            this.disabled = true;

            try {
                const res = await fetch(`https://api.hacienda.go.cr/fe/ae?identificacion=${identificacion}`);
                loading.style.display = 'none';
                this.disabled = false;

                if (!res.ok) throw new Error('No encontrado');
                const d = await res.json();

                // ── Auto-completar TODOS los campos del formulario ──

                // 1. Nombre / Razón Social
                const nombre = d.nombre || '';
                document.getElementById('cli-nombre').value = nombre;

                // 2. Tipo de ID (por longitud)
                const tipoSel = document.getElementById('cli-tipo-id');
                if      (identificacion.length === 9)  tipoSel.value = '01'; // Física
                else if (identificacion.length === 10) tipoSel.value = '02'; // Jurídica
                else if (identificacion.length === 11 || identificacion.length === 12) tipoSel.value = '03'; // DIMEX

                // 3. Actividad Económica → campo del formulario
                const actividades = (d.actividades || []).map(a => a.descripcion);
                const actividadTexto = actividades.join(' · ') || '—';
                document.getElementById('cli-actividad').value = actividades[0] || '';
                document.getElementById('mh-actividad-result').textContent = actividadTexto;

                // 4. Régimen Tributario → campo del formulario
                const regimen = d.regimen ? (d.regimen.descripcion || '') : '';
                document.getElementById('cli-regimen').value = regimen;
                document.getElementById('mh-regimen-result').textContent = regimen || '—';

                // 5. Estado tributario (solo visual en el panel)
                const estado = d.situacion ? d.situacion.estado : 'Desconocido';
                const esInscrito = estado === 'Inscrito';
                const estadoBg    = esInscrito ? '#d1fae5' : (estado === 'No inscrito' ? '#fee2e2' : '#fef9c3');
                const estadoColor = esInscrito ? '#065f46' : (estado === 'No inscrito' ? '#dc2626' : '#92400e');

                document.getElementById('mh-nombre-result').textContent = nombre;
                document.getElementById('mh-id-display').textContent = tipoSel.options[tipoSel.selectedIndex].text + ' — ' + identificacion;

                const badge = document.getElementById('mh-estado-badge');
                badge.textContent = estado;
                badge.style.background = estadoBg;
                badge.style.color = estadoColor;

                panelOk.style.display = 'block';

                // Micro-animación: resaltar campos rellenados
                ['cli-nombre','cli-actividad','cli-regimen'].forEach(id => {
                    const el = document.getElementById(id);
                    el.style.transition = 'box-shadow 0.3s';
                    el.style.boxShadow = '0 0 0 3px rgba(16,185,129,0.3)';
                    setTimeout(() => el.style.boxShadow = '', 1500);
                });

            } catch (err) {
                loading.style.display = 'none';
                this.disabled = false;
                panelErr.style.display = 'block';
                panelErr.innerHTML = '<i class="fas fa-exclamation-triangle" style="margin-right:6px;"></i> No se encontró el contribuyente en Hacienda. Verifique el número e ingréselo manualmente.';
            }
        });

        // Enter en el campo identificación → dispara la consulta MH
        document.getElementById('cli-identificacion').addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('btn-consultar-mh').click();
            }
        });

        /* ── Registrar ────────────────────────────────────────────── */
        document.getElementById('addClientForm').addEventListener('submit', function (e) {

            e.preventDefault();
            const tipoId = document.getElementById('cli-tipo-id').value;
            const identificacion = document.getElementById('cli-identificacion').value.trim();
            const nombre = document.getElementById('cli-nombre').value.trim();
            const correo = document.getElementById('cli-correo').value.trim();
            const telefono = document.getElementById('cli-telefono').value.trim();
            const movil = document.getElementById('cli-movil').value.trim();
            const provincia = document.getElementById('cli-provincia').value;
            const canton = document.getElementById('cli-canton').value;
            const distrito = document.getElementById('cli-distrito').value;
            const barrio = document.getElementById('cli-barrio').value;
            const direccion = document.getElementById('cli-direccion').value.trim();

            if (!identificacion || !nombre) {
                Swal.fire('Campos requeridos', 'Complete la identificación y el nombre del cliente.', 'warning');
                return;
            }

            // Validaciones Estrictas MH 4.4
            const identLimpia = identificacion.replace(/\D/g, '');
            if (identLimpia !== identificacion) {
                Swal.fire('Formato Inválido', 'Hacienda exige que la identificación solo contenga números (sin guiones ni letras).', 'error');
                return;
            }
            if (tipoId === "01" && identificacion.length !== 9) {
                Swal.fire('Formato Inválido', 'La Cédula Física debe tener exactamente 9 dígitos según MH 4.4.', 'error');
                return;
            }
            if (tipoId === "02" && identificacion.length !== 10) {
                Swal.fire('Formato Inválido', 'La Cédula Jurídica debe tener exactamente 10 dígitos según MH 4.4.', 'error');
                return;
            }
            if (tipoId === "03" && (identificacion.length !== 11 && identificacion.length !== 12)) {
                Swal.fire('Formato Inválido', 'El DIMEX debe tener 11 o 12 dígitos según MH 4.4.', 'error');
                return;
            }
            if (tipoId === "04" && identificacion.length !== 10) {
                Swal.fire('Formato Inválido', 'El NITE debe tener exactamente 10 dígitos según MH 4.4.', 'error');
                return;
            }

            // Guardar en el mockDB centralizado
            window.muroDB.addCliente({ 
                tipoId, identificacion, nombre, correo, 
                telefono, movil, provincia, canton, distrito, barrio, direccion, regimen: 'general' 
            });
            
            clientes = window.muroDB.getClientes();
            renderTabla(clientes);
            actualizarBadge();
            this.reset();
            Swal.fire({ icon: 'success', title: 'Cliente registrado correctamente, normativa aprobada.', timer: 2000, showConfirmButton: false });
        });

        /* ── Filtrar ──────────────────────────────────────────────── */

        /* ======= MOTOR DE BUSQUEDA DE CLIENTES PREMIUM ======= */
        (function() {
            const input = document.getElementById('buscar-clientes');
            const dropdown = document.getElementById('clientes-dropdown');

            function closeDropdown() {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
            }

            input.addEventListener('input', function() {
                const q = this.value.trim().toLowerCase();
                if (q.length < 1) {
                    closeDropdown();
                    renderTabla(clientes); // Reset table filter
                    return;
                }

                const matches = clientes.filter(c => 
                    multiWordMatch(`${c.nombre} ${c.identificacion} ${c.correo || ''} ${c.telefono || ''} ${c.direccion || ''}`, q)
                );

                // Update table in real-time
                renderTabla(matches);

                // Show dropdown results
                dropdown.innerHTML = '';
                if (!matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron clientes</div>';
                    dropdown.style.display = 'block';
                    return;
                }

                matches.slice(0, 10).forEach(c => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `
                        <div class="autocomplete-info">
                            <div class="autocomplete-name">${c.nombre}</div>
                            <div class="autocomplete-subinfo">
                                <span class="autocomplete-badge">${c.tipoId}-${c.identificacion}</span>
                                <span style="opacity:0.7;"><i class="fas fa-envelope" style="margin-right:4px;"></i>${c.correo || 'S/C'}</span>
                            </div>
                        </div>
                        <div style="font-weight:800, color:#1e40af; font-size:0.75rem; background:#eff6ff; padding:4px 8px; border-radius:6px; white-space:nowrap;">
                            <i class="fas fa-user-check" style="margin-right:4px;"></i>ACTIVO
                        </div>
                    `;
                    item.onclick = () => {
                        input.value = c.nombre;
                        renderTabla([c]);
                        closeDropdown();
                    };
                    dropdown.appendChild(item);
                });
                dropdown.style.display = 'block';
            });

            document.addEventListener('click', closeDropdown);
            input.addEventListener('click', (e) => e.stopPropagation());
        })();


        /* ======= IMPORTACIÓN MASIVA EXCEL ======= */
        document.getElementById('file-upload-cli').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(evt) {
                const data = new Uint8Array(evt.target.result);
                const workbook = XLSX.read(data, {type: 'array'});
                const firstSheetName = workbook.SheetNames[0];
                const worksheet = workbook.Sheets[firstSheetName];
                const json = XLSX.utils.sheet_to_json(worksheet, {header: 1});
                
                let count = 0;
                for (let i = 1; i < json.length; i++) { // Omitir el header
                    const row = json[i];
                    if (!row || !row.length) continue;
                    
                    const c = {
                        id: Date.now() + i,
                        tipoId: row[0] || '01',
                        identificacion: row[1] || `000000000`,
                        nombre: row[2] || 'Cliente Importado',
                        correo: row[3] || '',
                        telefono: row[4] || '',
                        direccion: row[5] || '',
                        provincia: 'San José' // Default visual para tabla
                    };
                    if (window.muroDB) window.muroDB.addCliente(c);
                    count++;
                }
                clientes = window.muroDB.getClientes();
                renderTabla(clientes);
                actualizarBadge();
                Swal.fire('Gestión de Clientes', `Se importaron ${count} clientes correctamente.`, 'success');
                document.getElementById('file-upload-cli').value = '';
            };
            reader.readAsArrayBuffer(file);
        });

        /* ── Locaciones en cascada ────────────────────────────────── */
        let ubicacionData = window.ubicacionData || {};
        const provSelect = document.getElementById('cli-provincia');
        const cantonSelect = document.getElementById('cli-canton');
        const distSelect = document.getElementById('cli-distrito');
        const barrioSelect = document.getElementById('cli-barrio');

        // Convierte "SAN JOSE DE LA MONTAÑA" → "San José de la Montaña"
        const minusculas = new Set(['de','del','la','las','los','el','en','y','a','al','con','por','para','e','o','u']);
        function titleCase(str) {
            if (!str) return str;
            return str.toLowerCase().split(' ').map((word, i) => {
                if (i > 0 && minusculas.has(word)) return word;
                return word.charAt(0).toUpperCase() + word.slice(1);
            }).join(' ');
        }

        function initUbicaciones() {
            provSelect.innerHTML = '<option value="">Seleccionar Provincia...</option>';
            if (Object.keys(ubicacionData).length > 0) {
                Object.keys(ubicacionData).sort().forEach(prov => {
                    const opt = document.createElement('option');
                    opt.value = prov;
                    opt.textContent = titleCase(prov);
                    provSelect.appendChild(opt);
                });
            } else {
                provSelect.innerHTML = '<option value="">Error cargando ubicaciones (Script Faltante)</option>';
            }
        }
        initUbicaciones();

        provSelect.addEventListener('change', () => {
            cantonSelect.innerHTML = '<option value="">Seleccionar Cantón...</option>';
            distSelect.innerHTML = '<option value="">Seleccionar Distrito...</option>';
            barrioSelect.innerHTML = '<option value="">Seleccionar Barrio...</option>';
            if (!provSelect.value) return;

            const cantones = ubicacionData[provSelect.value] ? Object.keys(ubicacionData[provSelect.value]).sort() : [];
            cantones.forEach(canton => {
                const opt = document.createElement('option');
                opt.value = canton;
                opt.textContent = titleCase(canton);
                cantonSelect.appendChild(opt);
            });
        });

        cantonSelect.addEventListener('change', () => {
            distSelect.innerHTML = '<option value="">Seleccionar Distrito...</option>';
            barrioSelect.innerHTML = '<option value="">Seleccionar Barrio...</option>';
            const prov = provSelect.value;
            const canton = cantonSelect.value;
            if (!prov || !canton) return;

            const distritos = ubicacionData[prov][canton] ? Object.keys(ubicacionData[prov][canton]).sort() : [];
            distritos.forEach(dist => {
                const opt = document.createElement('option');
                opt.value = dist;
                opt.textContent = titleCase(dist);
                distSelect.appendChild(opt);
            });
        });

        distSelect.addEventListener('change', () => {
            barrioSelect.innerHTML = '<option value="">Seleccionar Barrio...</option>';
            const prov = provSelect.value;
            const canton = cantonSelect.value;
            const dist = distSelect.value;
            if (!prov || !canton || !dist) return;

            const barrios = ubicacionData[prov][canton][dist] || [];
            barrios.sort().forEach(barrio => {
                const opt = document.createElement('option');
                opt.value = barrio;
                opt.textContent = titleCase(barrio);
                barrioSelect.appendChild(opt);
            });
        });

        /* ── Renderizado Inicial ──────────────────────── */
        clientes = window.muroDB ? window.muroDB.getClientes() : [];
        renderTabla(clientes);
        actualizarBadge();
    })();
    


        const canvas = document.getElementById('particles-canvas');
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