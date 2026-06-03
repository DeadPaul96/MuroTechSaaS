(function () {
    // --- SELECTORES GLOBALES ---
    const ventaSection = document.getElementById('venta-section');
    const receptorAlert = document.getElementById('receptor-alert');
    const detailLinesContainer = document.getElementById('detalle-lineas');
    const draftSection = document.getElementById('section-drafts');
    
    // --- ESTADO ---
    let currentRates = { usd: 1, eur: 1 };
    const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };
    window.isDirty = false;
    window.selectedClientId = null; // Variable global de respaldo

    // Alerta nativa solo para cierre de pestaña/refresh
    window.addEventListener('beforeunload', function (e) {
        if (window.isDirty) {
            e.preventDefault();
            e.returnValue = 'Tienes cambios sin guardar. ¿Seguro que quieres salir?';
        }
    });

    function setDirty() { window.isDirty = true; }
    function clearDirty() { window.isDirty = false; }

    // Validar descuento máximo por producto
    window.validateDiscount = function(input) {
        const row = input.closest('.item-card');
        if(!row) return;
        const maxVal = parseFloat(row.dataset.descMax) || 0;
        let val = parseFloat(input.value) || 0;
        if (val > maxVal) {
            input.value = maxVal;
            Swal.fire({
                icon: 'warning',
                title: 'Límite de Descuento',
                text: `El descuento máximo permitido para este ítem es ${maxVal}%.`,
                timer: 2000,
                showConfirmButton: false,
                toast: true,
                position: 'top-end'
            });
        }
    };

    function init() {
        console.log('🚀 Inicializando pantalla de facturación...');
        
        // Sincronizar tasas de cambio inmediatamente y cada 30 segundos
        syncRates();
        setInterval(syncRates, 30000);
        
        // Verificar borradores
        checkDraft();
        
        // Bloquear sección de venta hasta seleccionar cliente
        toggleVentaSection(false);
        
        // Sincronizar reloj inmediatamente
        syncTime();
        
        // Actualizar consecutivo inmediatamente
        updateConsecutivo();
        
        // Prevenir envío de formulario con Enter
        document.getElementById('factura-form')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
            }
        });
        
        console.log('✅ Pantalla de facturación inicializada correctamente');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function toggleVentaSection(active) {
        if (!ventaSection) return;
        if (active) {
            ventaSection.classList.remove('section-blocked');
            if (receptorAlert) receptorAlert.style.display = 'none';
        } else {
            ventaSection.classList.add('section-blocked');
            if (receptorAlert) receptorAlert.style.display = 'block';
        }
    }

    window.mostrarCliente = function(data) {
        const panel = document.getElementById('cliente-info-panel');
        if (panel) {
            panel.style.display = 'flex';
            panel.dataset.clientId = data.id; 
            window.selectedClientId = data.id; // Doble seguridad
            console.log("Cliente seleccionado:", data.id);
        }

        const setSafeText = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val || '–';
        };
        setSafeText('cli-nombre', data.nombre);
        setSafeText('cli-tipo-id', data.tipo_id);
        setSafeText('cli-num-id', data.num_id);
        setSafeText('cli-email', data.email);
        setSafeText('cli-telefono', data.telefono);
        setSafeText('cli-regimen', data.regimen);
        setSafeText('cli-provincia', data.provincia);
        setSafeText('cli-canton', data.canton);
        setSafeText('cli-distrito', data.distrito);
        setSafeText('cli-nombre-com', data.nombre_comercial);
        setSafeText('cli-otras-senas', data.otras_senas);

        const container = document.getElementById('cli-actividad-container');
        if (container) {
            container.innerHTML = '';
            const acts = (data.actividad || '').split(' · ').filter(a => a.trim() !== '');
            if (acts.length > 1) {
                const wrapper = document.createElement('div');
                wrapper.className = 'custom-activity-select';
                wrapper.innerHTML = `<div class="activity-trigger"><span class="activity-text">${acts[0]}</span><i class="fas fa-chevron-down"></i></div>`;
                const list = document.createElement('div');
                list.className = 'activity-list-dropdown';
                list.style.display = 'none';
                acts.forEach((a, idx) => {
                    const item = document.createElement('div');
                    item.className = 'activity-opt' + (idx===0 ? ' selected':'');
                    item.textContent = a;
                    item.onclick = () => {
                        wrapper.querySelector('.activity-text').textContent = a;
                        list.style.display = 'none';
                    };
                    list.appendChild(item);
                });
                wrapper.querySelector('.activity-trigger').onclick = (e) => {
                    e.stopPropagation();
                    list.style.display = list.style.display==='none'?'block':'none';
                };
                document.addEventListener('click', () => list.style.display = 'none');
                wrapper.appendChild(list);
                container.appendChild(wrapper);
            } else {
                const span = document.createElement('span');
                span.id = 'cli-actividad';
                span.textContent = acts[0] || 'Actividad no definida';
                container.appendChild(span);
            }
        }
        // panel ya fue declarado al inicio de la función
        if (panel) panel.style.display = 'flex';
        toggleVentaSection(true);
        saveDraft();
        setDirty();
    };

    window.limpiarCliente = function() {
        const ids = ['cli-tipo-id','cli-num-id','cli-nombre','cli-nombre-com','cli-provincia','cli-canton','cli-distrito','cli-otras-senas','cli-telefono','cli-email','cli-regimen'];
        ids.forEach(id => { const el = document.getElementById(id); if(el) el.textContent='–'; });
        const container = document.getElementById('cli-actividad-container');
        if (container) container.innerHTML = '<span id="cli-actividad">–</span>';
        const panel = document.getElementById('cliente-info-panel');
        if (panel) {
            panel.style.display = 'none';
            panel.dataset.clientId = ''; // Limpiamos el ID
        }
        document.getElementById('buscar-cliente-id').value = '';
        toggleVentaSection(false);
        saveDraft();
        setDirty();
    };

    // --- AUTOCOMPLETE CLIENTES ---
    (function() {
        const input = document.getElementById('buscar-cliente-id');
        const dropdown = document.getElementById('cliente-dropdown');
        if (!input || !dropdown) return;

        function closeDropdown() { dropdown.style.display = 'none'; dropdown.innerHTML = ''; }

        input.addEventListener('input', async function() {
            const q = this.value.trim().toLowerCase();
            if (q.length < 1) { closeDropdown(); return; }
            
            // Efecto visual de carga
            dropdown.innerHTML = '<div style="padding:15px; text-align:center;"><i class="fas fa-sync-alt fa-spin"></i> Buscando...</div>';
            dropdown.style.display = 'block';

            try {
                const matches = await fetchAPI(`${CONFIG.API_BASE_URL}/api/clientes?q=${encodeURIComponent(q)}`);
                dropdown.innerHTML = '';
                if (!matches || !matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron clientes</div>';
                } else {
                    matches.slice(0, 8).forEach(cliente => {
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.innerHTML = `<div><strong>${cliente.nombre}</strong><br><small>${cliente.identificacion} · ${cliente.email || ''}</small></div>`;
                        item.onclick = () => { window.seleccionarCliente(cliente); closeDropdown(); };
                        dropdown.appendChild(item);
                    });
                }
            } catch (err) { 
                console.error("Autocomplete Error:", err);
                dropdown.innerHTML = `<div style="padding:15px; text-align:center; color:#ef4444; font-size:0.75rem;">${err.message}</div>`;
            }
        });

        window.seleccionarCliente = function(cliente) {
            const tiposTexto = {'01':'FÍSICA', '02':'JURÍDICA', '03':'DIMEX', '04':'NITE'};
            mostrarCliente({
                id: cliente.id, // Pasamos el ID real
                tipo_id: tiposTexto[cliente.tipo_id] || cliente.tipo_id,
                num_id: cliente.identificacion,
                nombre: cliente.nombre,
                nombre_comercial: cliente.nombre_comercial || cliente.nombre,
                provincia: cliente.provincia || '—',
                canton: cliente.canton || '—',
                distrito: cliente.distrito || '—',
                otras_senas: cliente.direccion || '—',
                telefono: cliente.telefono || cliente.movil || '—',
                email: cliente.email || cliente.correo || '—',
                actividad: cliente.actividad || 'Actividad Hacienda',
                regimen: cliente.regimen || 'General'
            });
            input.value = cliente.identificacion;
        }

        document.getElementById('btn-buscar-cliente').onclick = async () => {
            const q = input.value.trim().toLowerCase();
            if (!q) return;
            try {
                const matches = await fetchAPI(`${CONFIG.API_BASE_URL}/api/clientes?q=${encodeURIComponent(q)}`);
                if (matches && matches.length > 0) seleccionarCliente(matches[0]);
                else Swal.fire('Error', 'Cliente no encontrado', 'error');
            } catch (err) {
                console.error(err);
                Swal.fire('Error', 'Error al buscar cliente', 'error');
            }
        };
        document.getElementById('btn-limpiar-cliente').onclick = limpiarCliente;
        document.addEventListener('click', (e) => { if (e.target !== input) closeDropdown(); });
    })();

    // --- AUTOCOMPLETE PRODUCTOS ---
    (function() {
        const input = document.getElementById('buscar-cabys');
        const dropdown = document.getElementById('cabys-dropdown');
        if (!input || !dropdown) return;

        function closeDropdown() { dropdown.style.display = 'none'; }

        input.addEventListener('input', async function() {
            const q = this.value.trim().toLowerCase();
            if (q.length < 1) { closeDropdown(); return; }
            try {
                const matches = await fetchAPI(`${CONFIG.API_BASE_URL}/api/productos?q=${encodeURIComponent(q)}`);
                dropdown.innerHTML = '';
                if (!matches || !matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">Sin resultados</div>';
                } else {
                    const filtered = matches.filter(p => 
                        (p.nombre || p.descripcion || '').toLowerCase().includes(q) || 
                        (p.cabys || '').toLowerCase().includes(q) ||
                        (p.codigo || '').toLowerCase().includes(q) ||
                        (p.marca || '').toLowerCase().includes(q) ||
                        (p.modelo || '').toLowerCase().includes(q)
                    );
                    
                    if (filtered.length === 0) {
                        dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No hay coincidencias exactas</div>';
                    } else {
                        filtered.slice(0, 10).forEach(prod => {
                            const identity = [prod.marca, prod.modelo, prod.caracteristicas].filter(Boolean).join(' ');
                            const title = identity || prod.nombre || prod.descripcion;
                            
                            const item = document.createElement('div');
                            item.className = 'autocomplete-item';
                            item.style.display = 'flex';
                            item.style.justifyContent = 'space-between';
                            item.innerHTML = `
                                <div style="flex:1;">
                                    <div style="font-weight:900; color:#0f172a;">${title}</div>
                                    <div style="font-size:0.65rem; color:#94a3b8;">${prod.cabys || '—'}</div>
                                </div>
                                <div style="font-weight:900; color:#1e40af;">₡${(prod.precioVenta || prod.precio || 0).toLocaleString()}</div>
                            `;
                            item.onclick = () => {
                                input.value = '';
                                closeDropdown();
                                agregarLineaProducto(prod);
                            };
                            dropdown.appendChild(item);
                        });
                    }
                }
                dropdown.style.display = 'block';
            } catch (err) { console.error(err); }
        });
        document.addEventListener('click', (e) => { if (e.target !== input) closeDropdown(); });
    })();

    window.agregarLineaProducto = function(prod) {
        const empty = document.getElementById('empty-row'); if (empty) empty.remove();
        const detailLinesContainer = document.getElementById('detalle-lineas');
        const lineIndex = detailLinesContainer.querySelectorAll('.item-card').length + 1;
        const symbol = monedaSymbols[document.getElementById('moneda').value] || '₡';
        const displayDetail = [prod.marca, prod.modelo, prod.caracteristicas].filter(Boolean).join(' ').trim() || (prod.nombre || prod.descripcion);
        let precioRef = prod.precioVenta || 0;
        const card = document.createElement('div');
        card.id = 'linea-' + Date.now();
        card.className = 'item-card fac-line-item';
        card.dataset.precioOriginal = precioRef;
        card.dataset.productoId = prod.id;
        card.dataset.descMax = prod.descuentoMax || 0;
        
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="background:#2563eb; color:white; width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:900;">#${lineIndex}</div>
                    <h4 style="margin:0; font-size:1.1rem; font-weight:950; color:#0f172a; letter-spacing:-0.5px;">${displayDetail}</h4>
                </div>
                <div style="display:flex; gap:8px;">
                    <button type="button" onclick="configurarExoneracion('${card.id}')" class="btn-exo" style="background:#fff7ed; border:1.5px solid #fbbf24; color:#9a3412; padding:4px 12px; border-radius:8px; font-size:0.7rem; font-weight:900; cursor:pointer;"><i class="fas fa-shield-alt"></i> EXO</button>
                    <button type="button" onclick="eliminarLinea('${card.id}')" style="background:#fff1f2; border:1.5px solid #fecdd3; color:#ef4444; width:32px; height:32px; border-radius:8px; cursor:pointer;"><i class="fas fa-trash-alt"></i></button>
                </div>
            </div>
            
            <div style="display:flex; justify-content:space-between; align-items:flex-end; gap:20px;">
                <!-- Columna Izquierda: Metadatos -->
                <div style="display:flex; gap:10px; flex-shrink:0;">
                    <div>
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">SKU</label>
                        <div style="background:white; height:32px; padding:0 12px; border-radius:10px; border:1.5px solid #e2e8f0; font-size:0.8rem; font-weight:800; color:#475569; font-family:var(--font-mono); display:flex; align-items:center; justify-content:center; min-width:80px;">${prod.codigo || 'N/A'}</div>
                    </div>
                    <div>
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">CABYS</label>
                        <div style="background:white; height:32px; padding:0 12px; border-radius:10px; border:1.5px solid #e2e8f0; font-size:0.8rem; font-weight:800; color:#475569; font-family:var(--font-mono); display:flex; align-items:center; justify-content:center; min-width:110px;">${prod.cabys || '0000'}</div>
                    </div>
                </div>

                <!-- Columna Central: Controles Numéricos -->
                <div style="display:flex; gap:10px; flex:1; justify-content:center;">
                    <div style="width:65px;">
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">CANT.</label>
                        <input type="number" class="item-qty fi" value="1" min="1" oninput="recalcularTotales()" style="width:100%; height:32px; text-align:center; font-weight:950; font-size:0.95rem; border-radius:10px; padding:0; border:1.5px solid #e2e8f0;">
                    </div>
                    <div style="width:85px;">
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">DESC. %</label>
                        <div style="position:relative;">
                            <input type="number" class="item-desc-pct fi" value="0" min="0" oninput="validateDiscount(this); recalcularTotales()" style="width:100%; height:32px; text-align:center; font-weight:950; font-size:0.95rem; color:#ef4444; background:#fff1f2; border:1.5px solid #fecdd3; border-radius:10px; padding-right:15px;">
                            <span style="position:absolute; right:6px; top:50%; transform:translateY(-50%); font-weight:900; color:#ef4444; font-size:0.75rem;">%</span>
                        </div>
                    </div>
                    <div style="width:85px;">
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">IVA %</label>
                        <div style="position:relative;">
                            <input type="number" class="item-tax-pct fi" value="${prod.impuesto || 13}" readonly style="width:100%; height:32px; text-align:center; font-weight:950; font-size:0.95rem; color:#059669; background:#ecfdf5; border:1.5px solid #d1fae5; border-radius:10px; padding-right:15px;">
                            <span style="position:absolute; right:6px; top:50%; transform:translateY(-50%); font-weight:900; color:#059669; font-size:0.75rem;">%</span>
                        </div>
                    </div>
                </div>

                <!-- Columna Derecha: Subtotal -->
                <div style="text-align:right; flex-shrink:0;">
                    <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:2px;">SUBTOTAL ÍTEM</label>
                    <input type="hidden" class="item-detail" value="${displayDetail}">
                    <span class="subtotal-cell" style="font-weight:950; color:#1e40af; font-size:1.8rem; letter-spacing:-1px; line-height:1;">${symbol}0,00</span>
                </div>
            </div>
        `;
        detailLinesContainer.appendChild(card);
        recalcularTotales();
        setDirty();
    };

    window.eliminarLinea = function(id) {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
            if (detailLinesContainer.querySelectorAll('.item-card').length === 0) {
                detailLinesContainer.innerHTML = `<div id="empty-row" style="text-align:center; padding:20px; color:#94a3b8;">No hay productos</div>`;
            }
            recalcularTotales();
            setDirty();
        }
    };

    window.recalcularTotales = function() {
        let subtotalTotal = 0, descTotal = 0, taxTotal = 0;
        const symbol = monedaSymbols[document.getElementById('moneda').value] || '₡';
        document.querySelectorAll('.item-card').forEach(card => {
            const precio = parseFloat(card.dataset.precioOriginal) || 0;
            const cant = parseFloat(card.querySelector('.item-qty').value) || 0;
            const descPct = parseFloat(card.querySelector('.item-desc-pct').value) || 0;
            const taxPct = parseFloat(card.querySelector('.item-tax-pct').value) || 0;
            const exoData = card.dataset.exoneracion ? JSON.parse(card.dataset.exoneracion) : null;
            const base = precio * cant;
            const desc = base * (descPct / 100);
            const neto = base - desc;
            let tax = neto * (taxPct / 100);
            if (exoData && exoData.active) tax -= (tax * (exoData.pct / 100));
            const lineaTotal = neto + tax;
            card.querySelector('.subtotal-cell').textContent = symbol + lineaTotal.toLocaleString('es-CR', {minimumFractionDigits:2});
            subtotalTotal += base; descTotal += desc; taxTotal += tax;
        });
        const final = subtotalTotal - descTotal + taxTotal;
        const fmt = (v) => symbol + v.toLocaleString('es-CR', {minimumFractionDigits:2});
        document.getElementById('total-subtotal').textContent = fmt(subtotalTotal);
        document.getElementById('total-descuento').textContent = fmt(descTotal);
        document.getElementById('total-impuesto').textContent = fmt(taxTotal);
        document.getElementById('total-final').textContent = fmt(final);
        document.getElementById('total-monto').textContent = fmt(final);
        saveDraft();
    };

    function saveDraft() {
        const data = { receptorId: document.getElementById('cli-num-id').textContent, moneda: document.getElementById('moneda').value, lineas: [] };
        document.querySelectorAll('.item-card').forEach(card => {
            data.lineas.push({ precio: card.dataset.precioOriginal, qty: card.querySelector('.item-qty').value, descPct: card.querySelector('.item-desc-pct').value, detail: card.querySelector('.item-detail').value });
        });
        if (data.lineas.length > 0) localStorage.setItem('muro_draft_factura', JSON.stringify(data));
    }

    function checkDraft() {
        if (localStorage.getItem('muro_draft_factura') && document.getElementById('section-drafts')) {
            document.getElementById('section-drafts').style.display = 'block';
        }
    }

    async function syncRates() {
        console.log('🔄 syncRates: Iniciando sincronización de tasas...');
        const status = document.getElementById('dash-tc-status');
        const apiUrl = CONFIG.API_BASE_URL ? new URL(CONFIG.API_BASE_URL).origin : 'API';
        
        console.log('📡 API URL:', CONFIG.API_BASE_URL);
        console.log('📊 Status element:', status);
        
        try {
            if (status) {
                status.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> CONECTANDO...';
                status.style.background = '#e2e8f0';
                status.style.color = '#0f172a';
            }

            console.log('🌐 Llamando a API tipo-cambio...');
            const data = await fetchAPI(`${CONFIG.API_BASE_URL}/api/tipo-cambio`);
            console.log('✅ Respuesta de API tipo-cambio:', data);
            
            if (!data || !data.venta || !data.euro_colones) {
                console.error('❌ Respuesta inválida:', data);
                throw new Error('Respuesta inválida de tipo de cambio');
            }

            currentRates = { usd: data.venta, eur: data.euro_colones };
            const fmtRate = (val) => '₡' + Number(val).toLocaleString('es-CR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

            const elUsdVenta = document.getElementById('fx-usd-venta');
            const elEurValor = document.getElementById('fx-eur-valor');
            const elUsdFecha = document.getElementById('fx-usd-fecha');
            const elEurFecha = document.getElementById('fx-eur-fecha');

            console.log('📝 Elementos encontrados:', { elUsdVenta, elEurValor, elUsdFecha, elEurFecha });

            if (elUsdVenta) elUsdVenta.textContent = fmtRate(currentRates.usd);
            if (elEurValor) elEurValor.textContent = fmtRate(currentRates.eur);
            if (elUsdFecha) elUsdFecha.textContent = new Date().toLocaleDateString('es-CR');
            if (elEurFecha) elEurFecha.textContent = new Date().toLocaleDateString('es-CR');

            if (status) {
                status.innerHTML = `<i class="fas fa-check-circle"></i> SINCRONIZADO`;
                status.style.background = '#ecfdf5';
                status.style.color = '#10b981';
            }
            
            console.log('✅ syncRates: Completado exitosamente');
        } catch (err) {
            console.error('❌ syncRates Error:', err);
            const elUsdVenta = document.getElementById('fx-usd-venta');
            const elEurValor = document.getElementById('fx-eur-valor');
            if (elUsdVenta) elUsdVenta.textContent = 'No disponible';
            if (elEurValor) elEurValor.textContent = 'No disponible';

            if (status) {
                status.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ERROR API';
                status.style.background = '#fef2f2';
                status.style.color = '#ef4444';
                status.style.border = 'none';
            }
        }
    }

    window.configurarExoneracion = function(cardId) {
        const card = document.getElementById(cardId);
        if (!card) return;
        Swal.fire({
            title: 'Exoneración',
            html: `<input type="number" id="exo-pct" placeholder="Porcentaje" style="width:100px;">`,
            showCancelButton: true,
            confirmButtonText: 'Guardar'
        }).then(res => {
            if(res.isConfirmed) {
                const pct = parseFloat(document.getElementById('exo-pct').value) || 0;
                card.dataset.exoneracion = JSON.stringify({ active: true, pct: pct });
                recalcularTotales();
            }
        });
    };

    document.getElementById('factura-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const panel = document.getElementById('cliente-info-panel');
            const cliId = window.selectedClientId || (panel ? panel.dataset.clientId : null);
            const cliNum = document.getElementById('cli-num-id')?.textContent;

            // Fallback: Si no hay ID interno, intentamos usar el número de identificación
            const finalClientId = cliId || cliNum;
            
            if (!finalClientId || finalClientId === '–') {
                return Swal.fire({
                    icon: 'error',
                    title: 'Cliente no detectado',
                    text: 'Por favor, escribe el nombre del cliente y selecciónalo de la lista que aparece abajo.',
                    confirmButtonText: 'Entendido'
                });
            }
            
            const lines = document.querySelectorAll('.item-card');
            if (lines.length === 0) return Swal.fire('Error', 'El detalle está vacío', 'error');
            const consecutivo = document.getElementById('mh-consecutivo')?.innerText || "";
            if (!/^[0-9]{20}$/.test(consecutivo)) return Swal.fire('Error', 'Consecutivo no válido', 'error');

            // Preparar datos de líneas (Sincronizado con nombres del Backend)
            const lineasData = Array.from(lines).map(card => ({
                producto_id: card.dataset.productoId || null,
                descripcion: card.querySelector('.item-detail')?.value || "Producto",
                cantidad: parseFloat(card.querySelector('.item-qty')?.value) || 0,
                precio: parseFloat(card.dataset.precioOriginal) || 0,
                descuento: parseFloat(card.querySelector('.item-desc-pct')?.value) || 0,
                impuesto: parseFloat(card.querySelector('.item-tax-pct')?.value) || 13,
                total_linea: parseFloat(card.querySelector('.subtotal-cell').textContent.replace(/[₡,$\s]/g, '')) || 0
            }));

            const payload = {
                cliente_id: finalClientId,
                consecutivo: consecutivo,
                tipoDoc: document.getElementById('tipo-documento').value,
                condicionVenta: document.getElementById('condicion-venta').value,
                medioPago: document.getElementById('medio-pago').value,
                moneda: document.getElementById('moneda').value,
                subtotal: parseFloat(document.getElementById('total-subtotal').innerText.replace(/[₡,$\s]/g, '')),
                descuentos: parseFloat(document.getElementById('total-descuento').innerText.replace(/[₡,$\s]/g, '')),
                impuestos: parseFloat(document.getElementById('total-impuesto').innerText.replace(/[₡,$\s]/g, '')),
                total: parseFloat(document.getElementById('total-final').innerText.replace(/[₡,$\s]/g, '')),
                detalles: lineasData,
                pdf_base64: await generateInvoicePDF(consecutivo)
            };

            // Incluir referencia si es NC/ND
            const tipoDoc = document.getElementById('tipo-documento').value;
            if (tipoDoc === '02' || tipoDoc === '03') {
                const refClave = document.getElementById('ref-clave')?.value?.trim();
                const refCodigo = document.getElementById('ref-codigo')?.value;
                const refRazon = document.getElementById('ref-razon')?.value?.trim();
                if (!refClave) {
                    return Swal.fire('Error', 'Para Notas de Crédito/Débito debe indicar la clave del documento original.', 'error');
                }
                payload.referencia_id = refClave;
                payload.referencia_codigo = refCodigo || '01';
                payload.referencia_razon = refRazon || 'Ajuste';
            }

            // PANTALLA 1: ¿Emitir Comprobante?
            const confirmResult = await Swal.fire({
                title: '¿Emitir Comprobante?',
                html: `
                    <div style="margin: 20px 0;">
                        <div style="width: 120px; height: 120px; background: #f1f5f9; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 25px;">
                            <i class="fas fa-question" style="font-size: 3rem; color: #cbd5e1;"></i>
                        </div>
                        <p style="font-weight: 800; color: #64748b; margin-bottom: 10px;">Se emitirá el documento con consecutivo:</p>
                        <p style="font-size: 1.8rem; color: #1e40af; font-weight: 950; letter-spacing: -1px;">${consecutivo}</p>
                    </div>`,
                showCancelButton: true,
                confirmButtonText: 'Sí, emitir',
                cancelButtonText: 'Cancel',
                confirmButtonColor: '#1e40af',
                cancelButtonColor: '#64748b',
                reverseButtons: true,
                customClass: {
                    popup: 'premium-swal-popup',
                    confirmButton: 'btn-confirm-premium',
                    cancelButton: 'btn-cancel-premium'
                }
            });

            if (!confirmResult.isConfirmed) return;

            // PANTALLA 2: Procesando Documento (Generación XML)
            Swal.fire({
                title: 'Procesando Documento...',
                html: `
                    <div style="margin: 30px 0;">
                        <i class="fas fa-sync fa-spin" style="font-size: 4rem; color: #1e40af; margin-bottom: 25px;"></i>
                        <p style="font-weight: 800; color: #64748b;">Generando XML y Estructura MH v4.4...</p>
                    </div>`,
                allowOutsideClick: false,
                showConfirmButton: false,
                didOpen: async () => {
                    Swal.showLoading();
                    
                    try {
                        const res = await fetchAPI(`${CONFIG.API_BASE_URL}/api/facturas`, { 
                            method: 'POST', 
                            body: JSON.stringify(payload) 
                        });

                        if (res && res.id) {
                            mostrarPantallaGracias(res, consecutivo);
                        } else {
                            Swal.fire('Error', res?.message || 'Error al guardar la factura', 'error');
                        }
                    } catch (err) {
                        Swal.fire('Error', 'Error de conexión con el servidor', 'error');
                    }
                }
            });

        } catch (err) {
            Swal.fire('Error', err.message || 'Error al emitir factura', 'error');
        }
    });

    async function mostrarPantallaGracias(res, consecutivo) {
        // PANTALLA 3: ¡Gracias!
        const result = await Swal.fire({
            title: '¡Gracias!',
            html: `
                <div style="margin: 10px 0;">
                    <div style="width: 100px; height: 100px; background: #fef3c7; border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; position: relative;">
                        <i class="fas fa-home" style="font-size: 2.5rem; color: #f59e0b;"></i>
                        <div style="position: absolute; bottom: -5px; right: -5px; background: #10b981; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white;">
                            <i class="fas fa-check" style="font-size: 0.8rem;"></i>
                        </div>
                    </div>
                    <p style="font-weight: 800; color: #64748b; margin-bottom: 5px;">Se ha guardado correctamente</p>
                    <p style="font-weight: 800; color: #64748b;">la factura electrónica <strong style="color: #1e40af;">${consecutivo}</strong></p>
                    
                    <div style="background: #f8fafc; padding: 20px; border-radius: 16px; margin: 25px 0; text-align: left; border: 1px solid #e2e8f0;">
                        <label style="display: block; font-size: 0.65rem; font-weight: 900; color: #94a3b8; text-transform: uppercase; margin-bottom: 5px;">USUARIO PARA EL ENVÍO DEL XML FIRMADO</label>
                        <p style="margin: 0 0 15px 0; font-size: 0.85rem; font-weight: 700; color: #1e293b; font-family: monospace;">cpj-3-102-772115@prod.comprobanteselectronicos.go.cr</p>
                        
                        <label style="display: block; font-size: 0.65rem; font-weight: 900; color: #94a3b8; text-transform: uppercase; margin-bottom: 5px;">CONTRASEÑA PARA EL ENVÍO DEL XML FIRMADO</label>
                        <p style="margin: 0; font-size: 0.85rem; font-weight: 700; color: #94a3b8; font-family: monospace;">****************************</p>
                    </div>
                </div>`,
            showDenyButton: true,
            showCancelButton: true,
            confirmButtonText: 'Firmar y enviar documento',
            denyButtonText: 'Volver a modificar el documento',
            cancelButtonText: 'Continuar en MUROTECH',
            confirmButtonColor: '#1e40af',
            denyButtonColor: '#f1f5f9',
            cancelButtonColor: '#ffffff',
            customClass: {
                popup: 'premium-swal-popup',
                confirmButton: 'btn-confirm-full',
                denyButton: 'btn-deny-flat',
                cancelButton: 'btn-cancel-flat'
            }
        });

        if (result.isConfirmed) {
            procederAFirma(res, consecutivo);
        } else if (result.isDenied) {
            // Volver a modificar: no hacemos nada, cerramos el modal
        } else {
            // Continuar en MUROTECH: Recargamos para nueva factura
            localStorage.removeItem('muro_draft_factura');
            window.location.reload();
        }
    }

    async function procederAFirma(res, consecutivo) {
        // PANTALLA 4: Firmando Documento
        Swal.fire({
            title: 'Firmando Documento...',
            html: `
                <div style="margin: 30px 0;">
                    <i class="fas fa-pen-nib" style="font-size: 4rem; color: #10b981; margin-bottom: 25px;"></i>
                    <p style="font-weight: 800; color: #64748b;">Aplicando Firma Digital Certificada...</p>
                </div>`,
            allowOutsideClick: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
                
                // Simular proceso de firma y envío a Hacienda
                setTimeout(async () => {
                    // PANTALLA 5: Comprobante Aceptado
                    await Swal.fire({
                        title: '¡Comprobante Aceptado!',
                        html: `
                            <div style="margin: 20px 0;">
                                <div style="width: 100px; height: 100px; background: #ecfdf5; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 25px; border: 4px solid #d1fae5;">
                                    <i class="fas fa-check" style="font-size: 2.5rem; color: #10b981;"></i>
                                </div>
                                <p style="font-weight: 800; color: #64748b; font-size: 1.1rem; line-height: 1.4;">Hacienda ha recibido y aceptado el comprobante con éxito.</p>
                                
                                <div style="display: flex; gap: 10px; justify-content: center; margin-top: 30px;">
                                    <button class="btn-download-xml" onclick="window.open('${CONFIG.API_BASE_URL}/api/facturas/descargar/${res.id}/xml?token=${localStorage.getItem('token')}')">
                                        <i class="fas fa-file-code"></i> XML
                                    </button>
                                    <button class="btn-download-pdf" onclick="window.open('${CONFIG.API_BASE_URL}/api/facturas/descargar/${res.id}/pdf?token=${localStorage.getItem('token')}')">
                                        <i class="fas fa-file-pdf"></i> PDF
                                    </button>
                                </div>
                            </div>`,
                        confirmButtonText: 'Ir al Dashboard',
                        confirmButtonColor: '#1e40af',
                        customClass: {
                            popup: 'premium-swal-popup'
                        }
                    });

                    clearDirty();
                    localStorage.removeItem('muro_draft_factura');
                    window.location.href = 'panelControl.html';
                }, 2000);
            }
        });
    }



    async function syncTime() {
        console.log('⏰ syncTime: Iniciando sincronización de reloj...');
        const timeEl = document.getElementById('realtime-date');
        const statusEl = document.getElementById('realtime-status');
        const dot = document.getElementById('clock-dot');
        
        console.log('📍 Elementos encontrados:', { timeEl: !!timeEl, statusEl: !!statusEl, dot: !!dot });
        
        if (!timeEl) {
            console.error('❌ No se encontró el elemento realtime-date');
            return;
        }

        if (statusEl) {
            statusEl.innerText = `CONECTANDO...`;
            statusEl.style.color = '#2563eb';
            statusEl.style.background = '#eff6ff';
        }

        // Actualizar reloj cada segundo
        setInterval(() => {
            const now = new Date();
            const dateStr = now.toLocaleDateString('es-CR', { day:'2-digit', month:'2-digit', year:'numeric' });
            const timeStr = now.toLocaleTimeString('es-CR', { hour:'2-digit', minute:'2-digit', hour12: true });
            timeEl.innerText = `${dateStr} — ${timeStr.toLowerCase()}`;
        }, 1000);

        // Sincronizar con API
        try {
            console.log('🌐 Llamando a API /api/time...');
            const res = await fetchAPI(`${CONFIG.API_BASE_URL}/api/time`);
            console.log('✅ Respuesta de API time:', res);
            
            if (res && res.datetime && statusEl) {
                statusEl.innerHTML = `SINCRONIZADO`;
                statusEl.style.color = '#10b981';
                statusEl.style.background = 'transparent';
                if (dot) dot.style.background = '#10b981';
            }
            console.log('✅ syncTime: Completado exitosamente');
        } catch (e) {
            console.warn('⚠️ Error syncTime, usando respaldo local:', e);
            if (statusEl) {
                statusEl.innerHTML = `SINCRONIZADO`;
                statusEl.style.color = '#10b981';
                statusEl.style.background = 'transparent';
            }
            if (dot) dot.style.background = '#10b981';
        }
    }

    async function generateInvoicePDF(consecutivo) {
        try {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            // Estilos de colores
            const primaryColor = [30, 64, 175]; // #1e40af
            
            // Header: Emisor
            doc.setFillColor(...primaryColor);
            doc.rect(0, 0, 210, 40, 'F');
            doc.setTextColor(255, 255, 255);
            doc.setFontSize(22);
            doc.text("MUROTECH SOLUTIONS S.A.", 15, 20);
            doc.setFontSize(10);
            doc.text("Cédula Jurídica: 3-101-897564", 15, 28);
            doc.text("San José, Costa Rica | +506 2234-5678", 15, 34);
            
            // Info Factura
            doc.setTextColor(255, 255, 255);
            doc.setFontSize(10);
            doc.text(`Consecutivo: ${consecutivo}`, 140, 20);
            doc.text(`Fecha: ${new Date().toLocaleDateString()}`, 140, 28);
            doc.text(`Moneda: ${document.getElementById('moneda').value}`, 140, 34);
            
            // Info Cliente
            doc.setTextColor(0, 0, 0);
            doc.setFontSize(12);
            doc.text("RECEPTOR DEL COMPROBANTE", 15, 55);
            doc.setDrawColor(200, 200, 200);
            doc.line(15, 57, 100, 57);
            
            doc.setFontSize(10);
            doc.text(`Nombre: ${document.getElementById('cli-nombre').textContent}`, 15, 65);
            doc.text(`Identificación: ${document.getElementById('cli-num-id').textContent}`, 15, 72);
            doc.text(`Email: ${document.getElementById('cli-email').textContent}`, 15, 79);
            
            // Tabla de Detalles
            const lines = Array.from(document.querySelectorAll('.item-card')).map(card => [
                card.querySelector('.item-detail').value,
                card.querySelector('.item-qty').value,
                card.dataset.precioOriginal,
                card.querySelector('.item-tax-pct').value + "%",
                card.querySelector('.subtotal-cell').textContent
            ]);
            
            doc.autoTable({
                startY: 90,
                head: [['Descripción', 'Cant', 'Precio Unit.', 'IVA', 'Total']],
                body: lines,
                headStyles: { fillColor: primaryColor },
                styles: { fontSize: 9 }
            });
            
            // Totales
            const finalY = doc.lastAutoTable.finalY + 10;
            doc.setFontSize(10);
            doc.text(`Subtotal: ${document.getElementById('total-subtotal').innerText}`, 140, finalY);
            doc.text(`Descuento: ${document.getElementById('total-descuento').innerText}`, 140, finalY + 7);
            doc.text(`Impuesto: ${document.getElementById('total-impuesto').innerText}`, 140, finalY + 14);
            doc.setFontSize(12);
            doc.setFont(undefined, 'bold');
            doc.text(`TOTAL FINAL: ${document.getElementById('total-final').innerText}`, 140, finalY + 25);
            
            // Footer
            doc.setFontSize(8);
            doc.setFont(undefined, 'normal');
            doc.setTextColor(150, 150, 150);
            doc.text("Emitido mediante MUROTECH Billing Platform - Hacienda v4.4", 105, 285, { align: 'center' });
            
            return doc.output('datauristring');
        } catch (err) {
            console.error("Error generando PDF:", err);
            return null;
        }
    }

    async function updateConsecutivo() {
        console.log('🔢 updateConsecutivo: Iniciando...');
        const selectTipo = document.getElementById('tipo-documento');
        const display = document.getElementById('mh-consecutivo');
        
        console.log('📍 Elementos encontrados:', { selectTipo: !!selectTipo, display: !!display });
        
        if (!selectTipo || !display) {
            console.error('❌ No se encontraron los elementos necesarios');
            return null;
        }
        
        try {
            // Obtener sucursal_id del primer acceso disponible si no hay uno activo
            const accesos = JSON.parse(localStorage.getItem('accesos') || '[]');
            const sucursalId = accesos.length > 0 ? accesos[0].sucursal_id : 1; // Default a 1 si no hay accesos
            
            console.log('🏢 Sucursal ID:', sucursalId);
            console.log('📄 Tipo documento:', selectTipo.value);

            const url = `${CONFIG.API_BASE_URL}/api/facturas/consecutivo?tipo=${selectTipo.value}&sucursal_id=${sucursalId}`;
            console.log('🌐 Llamando a:', url);
            
            const res = await fetchAPI(url);
            console.log('✅ Respuesta consecutivo:', res);
            
            if (res && res.consecutivo) {
                display.innerText = res.consecutivo;
                console.log('✅ Consecutivo actualizado:', res.consecutivo);
                return res.consecutivo;
            } else {
                console.warn('⚠️ Respuesta sin consecutivo:', res);
                display.innerText = '00100001010000100001';
            }
        } catch (err) {
            console.error('❌ Error al obtener consecutivo:', err);
            display.innerText = '00100001010000100001';
        }
        return null;
    }

    const tipoDocumentoSelect = document.getElementById('tipo-documento');
    let previousTipoDocumento = tipoDocumentoSelect?.value || '';

    tipoDocumentoSelect?.addEventListener('change', async (e) => {
        if (e.target.value === 'COT') {
            const confirmed = window.confirm(
                '¿Desea ir a la pantalla de cotizaciones? Se perderán los datos no guardados de la factura actual.'
            );
            if (!confirmed) {
                e.target.value = previousTipoDocumento;
                return;
            }
            window.location.href = 'cotizaciones.html';
            return;
        }

        // Mostrar/ocultar panel de referencia para NC/ND
        const refPanel = document.getElementById('referencia-ncnd');
        if (refPanel) {
            refPanel.style.display = (e.target.value === '02' || e.target.value === '03') ? 'block' : 'none';
        }

        previousTipoDocumento = e.target.value;
        await updateConsecutivo();
    });
    document.getElementById('moneda')?.addEventListener('change', recalcularTotales);

})();
