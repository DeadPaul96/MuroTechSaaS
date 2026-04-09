/**
 * MUROTECH SaaS - Registro de Usuario
 * Re-escrito para garantizar sincronización total con API de Hacienda de clientes.html
 */

// Estado Global de Actividades
let economicActivities = [];

document.addEventListener('DOMContentLoaded', () => {
    // 1. Inicializar Selects de Ubicación
    initUbicacionCascading();

    // 2. Inicializar Selects de Identificación
    loadTiposIdentificacion();

    // 3. Configurar Botón de Consulta Hacienda (ESPEJO DE CLIENTES.HTML)
    const btnConsultar = document.getElementById('btnConsultarCedula');
    const cedulaInput = document.getElementById('reg-cedula');
    
    if (btnConsultar) {
        btnConsultar.addEventListener('click', async function () {
            const identificacion = cedulaInput.value.trim().replace(/\D/g, '');
            
            if (!identificacion || identificacion.length < 9) {
                Swal.fire('', 'Ingrese un número de identificación válido (mínimo 9 dígitos).', 'warning');
                return;
            }

            const panelOk  = document.getElementById('mh-result-panel');
            const panelErr = document.getElementById('mh-error-panel');
            const loading  = document.getElementById('mh-loading');

            // Reset UI
            panelOk.style.display  = 'none';
            panelErr.style.display = 'none';
            loading.style.display  = 'block';
            this.disabled = true;

            try {
                // LA MISMA API EXACTA QUE EN CLIENTES.HTML
                const res = await fetch(`https://api.hacienda.go.cr/fe/ae?identificacion=${identificacion}`);
                loading.style.display = 'none';
                this.disabled = false;

                if (!res.ok) throw new Error('No encontrado');
                const d = await res.json();

                // ── AUTOCOMPLETAR FORMULARIO ──

                // A. Nombre / Razón Social
                const nombreLegal = d.nombre || '';
                document.getElementById('reg-razon').value = nombreLegal;
                document.getElementById('reg-empresa').value = nombreLegal; 
                
                // B. Primer Nombre (Seguridad)
                if (nombreLegal) {
                    const partes = nombreLegal.split(' ');
                    document.getElementById('reg-nombre').value = partes[0];
                }

                // C. Tipo de Identificación (Por longitud)
                const tipoSel = document.getElementById('reg-tipo-cedula');
                if (identificacion.length === 9) tipoSel.value = '01';
                else if (identificacion.length === 10) tipoSel.value = '02';
                else if (identificacion.length === 11 || identificacion.length === 12) tipoSel.value = '03';

                // D. Sincronizar Badge Visual
                updateIDBadge(identificacion);

                // E. Actividades Económicas (Usando el contenedor de Registro)
                economicActivities = [];
                const container = document.getElementById('actividades-container');
                if (container) container.innerHTML = '';
                
                if (d.actividades && d.actividades.length > 0) {
                    d.actividades.forEach(act => {
                        addActivityToRegistry(act.codigo, act.descripcion);
                    });
                }

                // F. Mostrar Panel de Telemetría (Estilo Clientes.html)
                document.getElementById('mh-nombre-result').textContent = nombreLegal;
                document.getElementById('mh-id-display').textContent = tipoSel.options[tipoSel.selectedIndex].text + ' — ' + identificacion;
                
                const actDesc = (d.actividades || []).map(a => a.descripcion).join(' · ');
                document.getElementById('mh-actividad-result').textContent = actDesc || '—';
                document.getElementById('mh-regimen-result').textContent = d.regimen ? (d.regimen.descripcion || 'General') : 'General';

                const badge = document.getElementById('mh-estado-badge');
                if (badge) {
                    const estado = d.situacion ? d.situacion.estado : 'Inscrito';
                    const isOk = estado === 'Inscrito';
                    badge.textContent = estado;
                    badge.style.background = isOk ? '#d1fae5' : '#fee2e2';
                    badge.style.color = isOk ? '#065f46' : '#dc2626';
                }

                panelOk.style.display = 'block';

                // Animación de Éxito
                ['reg-razon', 'reg-empresa'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.style.boxShadow = '0 0 0 3px rgba(16,185,129,0.3)';
                        setTimeout(() => el.style.boxShadow = '', 2000);
                    }
                });

            } catch (err) {
                loading.style.display = 'none';
                this.disabled = false;
                panelErr.style.display = 'block';
                panelErr.innerHTML = '<i class="fas fa-exclamation-triangle" style="margin-right:6px;"></i> No se encontró el contribuyente en Hacienda. Verifique el número e ingréselo manualmente.';
            }
        });
    }

    // Enter KEY trigger
    if (cedulaInput) {
        cedulaInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                btnConsultar.click();
            }
        });
        
        // Auto-detección visual al escribir
        cedulaInput.addEventListener('input', () => {
            updateIDBadge(cedulaInput.value.replace(/\D/g, ''));
        });
    }

    // 4. Configurar Botón Añadir Actividad Manual
    const btnAddManual = document.getElementById('btnAddActividad');
    if (btnAddManual) {
        btnAddManual.addEventListener('click', () => {
            const cod = document.getElementById('new-act-codigo').value.trim();
            const des = document.getElementById('new-act-desc').value.trim();
            if (cod.length === 6 && des) {
                addActivityToRegistry(cod, des);
                document.getElementById('new-act-codigo').value = '';
                document.getElementById('new-act-desc').value = '';
            } else {
                Swal.fire('Atención', 'Ingrese código de 6 dígitos y descripción.', 'info');
            }
        });
    }

    // 5. Password Toggles
    document.querySelectorAll('.password-toggle').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            const isPass = input.type === 'password';
            input.type = isPass ? 'text' : 'password';
            icon.className = isPass ? 'fas fa-eye-slash' : 'fas fa-eye';
        });
    });
});

// --- FUNCIONES HELPER ---

function addActivityToRegistry(codigo, desc) {
    const isPrincipal = economicActivities.length === 0;
    economicActivities.push({ codigo, desc, isPrincipal });
    renderActivities();
}

function renderActivities() {
    const container = document.getElementById('actividades-container');
    if (!container) return;
    container.innerHTML = '';
    
    economicActivities.forEach((act, idx) => {
        const div = document.createElement('div');
        div.className = 'activity-item';
        div.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:rgba(0,0,0,0.02); padding:10px 15px; border-radius:12px; margin-bottom:10px; border:1px solid rgba(0,0,0,0.05);';
        
        div.innerHTML = `
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="font-family:monospace; font-weight:800; color:var(--primary); font-size:0.9rem;">${act.codigo}</span>
                <span style="font-weight:700; color:var(--text-dark); font-size:0.85rem;">${act.desc}</span>
                ${act.isPrincipal ? '<span style="background:#d1fae5; color:#065f46; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:10px; text-transform:uppercase;">Principal</span>' : ''}
            </div>
            <button type="button" onclick="removeActivity(${idx})" style="background:none; border:none; color:#ef4444; cursor:pointer; font-size:0.9rem;">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

window.removeActivity = (idx) => {
    economicActivities.splice(idx, 1);
    if (economicActivities.length > 0 && !economicActivities.some(a => a.isPrincipal)) {
        economicActivities[0].isPrincipal = true;
    }
    renderActivities();
};

function updateIDBadge(val) {
    const badge = document.getElementById('id-detection-badge');
    if (!badge) return;
    
    if (val.length === 9) {
        badge.textContent = 'CÉDULA FÍSICA';
        badge.style.background = 'var(--primary)';
    } else if (val.length === 10) {
        badge.textContent = val.startsWith('3') ? 'CÉDULA JURÍDICA' : 'NITE';
        badge.style.background = val.startsWith('3') ? '#f59e0b' : '#8b5cf6';
    } else if (val.length >= 11) {
        badge.textContent = 'DIMEX';
        badge.style.background = '#10b981';
    } else {
        badge.textContent = 'DETECTANDO...';
        badge.style.background = '#94a3b8';
    }
}

function initUbicacionCascading() {
    const provSel = document.getElementById('reg-provincia');
    const canSel = document.getElementById('reg-canton');
    const disSel = document.getElementById('reg-distrito');
    const barSel = document.getElementById('reg-pueblo');

    if (!window.ubicacionData) return;

    // Poblar provincias
    provSel.innerHTML = '<option value="" disabled selected>Provincia</option>';
    Object.keys(window.ubicacionData).forEach(p => {
        provSel.innerHTML += `<option value="${p}">${p}</option>`;
    });

    provSel.onchange = () => {
        const p = provSel.value;
        canSel.innerHTML = '<option value="" disabled selected>Cantón</option>';
        Object.keys(window.ubicacionData[p]).forEach(c => {
            canSel.innerHTML += `<option value="${c}">${c}</option>`;
        });
        disSel.innerHTML = '<option value="" disabled selected>Distrito</option>';
        barSel.innerHTML = '<option value="" disabled selected>Barrio / Pueblo</option>';
    };

    canSel.onchange = () => {
        const p = provSel.value;
        const c = canSel.value;
        disSel.innerHTML = '<option value="" disabled selected>Distrito</option>';
        Object.keys(window.ubicacionData[p][c]).forEach(d => {
            disSel.innerHTML += `<option value="${d}">${d}</option>`;
        });
        barSel.innerHTML = '<option value="" disabled selected>Barrio / Pueblo</option>';
    };

    disSel.onchange = () => {
        const p = provSel.value;
        const c = canSel.value;
        const d = disSel.value;
        barSel.innerHTML = '<option value="" disabled selected>Barrio / Pueblo</option>';
        window.ubicacionData[p][c][d].forEach(b => {
            barSel.innerHTML += `<option value="${b}">${b}</option>`;
        });
    };
}

function loadTiposIdentificacion() {
    const sel = document.getElementById('reg-tipo-cedula');
    if (!sel) return;
    const types = [
        { c: '01', d: '01 - Cédula Física' },
        { c: '02', d: '02 - Cédula Jurídica' },
        { c: '03', d: '03 - DIMEX' },
        { c: '04', d: '04 - NITE' }
    ];
    sel.innerHTML = '<option value="" disabled selected>Tipo de identificación</option>';
    types.forEach(t => {
        sel.innerHTML += `<option value="${t.c}">${t.d}</option>`;
    });
}
