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
        syncRates();
        setInterval(syncRates, 30000);
        checkDraft();
        toggleVentaSection(false);
        syncTime();
        updateConsecutivo();
        
        document.getElementById('factura-form')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
            }
        });
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
        const panel = document.getElementById('cliente-info-panel');
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
        document.getElementById('cliente-info-panel').style.display = 'none';
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
                actividad: cliente.actividad_economica || cliente.actividad || 'Actividad Hacienda',
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
                                <div style="font-weight:900; color:#1e40af;">₡${(prod.precio_venta || prod.precio || 0).toLocaleString()}</div>
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
        let precioRef = prod.precio_venta || 0;
        const card = document.createElement('div');
        card.id = 'linea-' + Date.now();
        card.className = 'item-card fac-line-item';
        card.dataset.precioOriginal = precioRef;
        card.dataset.productoId = prod.id;
        card.dataset.descMax = prod.descuento_maximo || 0;
        
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
            
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <!-- Columna Izquierda: Metadatos -->
                <div style="display:flex; gap:12px;">
                    <div>
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px;">SKU</label>
                        <div style="background:white; padding:6px 10px; border-radius:8px; border:1.5px solid #e2e8f0; font-size:0.75rem; font-weight:800; color:#64748b; font-family:var(--font-mono);">${prod.codigo || 'N/A'}</div>
                    </div>
                    <div>
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px;">CABYS</label>
                        <div style="background:white; padding:6px 10px; border-radius:8px; border:1.5px solid #e2e8f0; font-size:0.75rem; font-weight:800; color:#64748b; font-family:var(--font-mono);">${prod.cabys || '0000'}</div>
                    </div>
                </div>

                <!-- Columna Derecha: Controles Numéricos -->
                <div style="display:flex; flex-direction:column; align-items:flex-end;">
                    <div style="display:flex; gap:12px;">
                        <div style="width:65px;">
                            <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">CANT.</label>
                            <input type="number" class="item-qty fi" value="1" min="1" oninput="recalcularTotales()" style="width:100%; height:34px; text-align:center; font-weight:950; font-size:1rem; border-radius:10px; padding:0;">
                        </div>
                        <div style="width:80px;">
                            <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">DESC. %</label>
                            <div style="position:relative;">
                                <input type="number" class="item-desc-pct fi" value="0" min="0" oninput="validateDiscount(this); recalcularTotales()" style="width:100%; height:34px; text-align:center; font-weight:950; font-size:1rem; color:#ef4444; background:#fff1f2; border-color:#fecdd3; border-radius:10px; padding-right:20px;">
                                <span style="position:absolute; right:8px; top:50%; transform:translateY(-50%); font-weight:900; color:#ef4444; font-size:0.8rem;">%</span>
                            </div>
                        </div>
                        <div style="width:80px;">
                            <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">IVA %</label>
                            <div style="position:relative;">
                                <input type="number" class="item-tax-pct fi" value="${prod.impuesto || 13}" readonly style="width:100%; height:34px; text-align:center; font-weight:950; font-size:1rem; color:#059669; background:#ecfdf5; border-color:#d1fae5; border-radius:10px; padding-right:20px;">
                                <span style="position:absolute; right:8px; top:50%; transform:translateY(-50%); font-weight:900; color:#059669; font-size:0.8rem;">%</span>
                            </div>
                        </div>
                    </div>
                    
                    <div style="text-align:right; margin-top:16px;">
                        <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:2px;">SUBTOTAL ÍTEM</label>
                        <input type="hidden" class="item-detail" value="${displayDetail}">
                        <span class="subtotal-cell" style="font-weight:950; color:#1e40af; font-size:2rem; letter-spacing:-1px; line-height:1;">${symbol}0,00</span>
                    </div>
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
        const status = document.getElementById('dash-tc-status');
        const apiUrl = CONFIG.API_BASE_URL ? new URL(CONFIG.API_BASE_URL).origin : 'API';
        try {
            if (status) {
                status.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> CONECTANDO...';
                status.style.background = '#e2e8f0';
                status.style.color = '#0f172a';
            }

            const data = await fetchAPI(`${CONFIG.API_BASE_URL}/api/tipo-cambio`);
            if (!data || !data.usd || !data.eur) throw new Error('Respuesta inválida de tipo de cambio');

            currentRates = { usd: data.usd.venta, eur: data.eur.valor };
            const fmtRate = (val) => '₡' + Number(val).toLocaleString('es-CR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

            const elUsdVenta = document.getElementById('fx-usd-venta');
            const elEurValor = document.getElementById('fx-eur-valor');
            const elUsdFecha = document.getElementById('fx-usd-fecha');
            const elEurFecha = document.getElementById('fx-eur-fecha');

            if (elUsdVenta) elUsdVenta.textContent = fmtRate(currentRates.usd);
            if (elEurValor) elEurValor.textContent = fmtRate(currentRates.eur);
            if (elUsdFecha) elUsdFecha.textContent = data.usd.fecha || '--/--/--';
            if (elEurFecha) elEurFecha.textContent = data.eur.fecha || '--/--/--';

            if (status) {
                status.innerHTML = `<i class="fas fa-check-circle"></i> SINCRONIZADO`;
                status.style.background = '#ecfdf5';
                status.style.color = '#10b981';
            }
        } catch (err) {
            console.warn('SyncRates API falló:', err);
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
            const clientId = document.getElementById('cliente-info-panel').dataset.clientId;
            if (!clientId) return Swal.fire('Error', 'Debe seleccionar un cliente del catálogo', 'error');
            const lines = document.querySelectorAll('.item-card');
            if (lines.length === 0) return Swal.fire('Error', 'El detalle está vacío', 'error');
            const consecutivo = document.getElementById('mh-consecutivo')?.innerText || "";
            if (!/^[0-9]{20}$/.test(consecutivo)) return Swal.fire('Error', 'Consecutivo no válido', 'error');

            const confirm = await Swal.fire({
                title: '¿Emitir Comprobante?',
                html: `<p>Se emitirá el documento oficial: <strong>${consecutivo}</strong></p>`,
                showCancelButton: true,
                confirmButtonText: 'Sí, emitir',
                cancelButtonText: 'Cancelar'
            });

            if (!confirm.isConfirmed) return;

            Swal.fire({ title: 'Emitiendo...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

            const lineasData = Array.from(lines).map(card => ({
                producto_id: card.dataset.productoId || null,
                descripcion: card.querySelector('.item-detail')?.value || "Producto",
                cantidad: parseFloat(card.querySelector('.item-qty')?.value) || 0,
                precio_unitario: parseFloat(card.dataset.precioOriginal) || 0,
                descuento_pct: parseFloat(card.querySelector('.item-desc-pct')?.value) || 0,
                impuesto_pct: parseFloat(card.querySelector('.item-tax-pct')?.value) || 13,
                total_linea: parseFloat(card.querySelector('.subtotal-cell').textContent.replace(/[₡,$\s]/g, '')) || 0
            }));

            const payload = {
                cliente_id: parseInt(clientId),
                consecutivo: consecutivo,
                tipo_documento: document.getElementById('tipo-documento').options[document.getElementById('tipo-documento').selectedIndex].text,
                condicion_venta: document.getElementById('condicion-venta').value,
                medio_pago: document.getElementById('medio-pago').value,
                moneda: document.getElementById('moneda').value,
                subtotal: parseFloat(document.getElementById('total-subtotal').innerText.replace(/[₡,$\s]/g, '')),
                descuentos: parseFloat(document.getElementById('total-descuento').innerText.replace(/[₡,$\s]/g, '')),
                impuestos: parseFloat(document.getElementById('total-impuesto').innerText.replace(/[₡,$\s]/g, '')),
                total: parseFloat(document.getElementById('total-final').innerText.replace(/[₡,$\s]/g, '')),
                lineas: lineasData
            };

            const res = await fetchAPI(`${CONFIG.API_BASE_URL}/api/facturas`, { method: 'POST', body: JSON.stringify(payload) });

            if (res && res.id) {
                clearDirty();
                localStorage.removeItem('muro_draft_factura');
                await Swal.fire('¡Éxito!', 'Factura emitida y guardada en base de datos.', 'success');
                await updateConsecutivo();
                window.location.reload();
            }
        } catch (err) { Swal.fire('Error', err.message || 'Error al emitir factura', 'error'); }
    });

    async function syncTime() {
        const timeEl = document.getElementById('realtime-date');
        const statusEl = document.getElementById('realtime-status');
        const dot = document.getElementById('clock-dot');
        if (!timeEl) return;

        const apiUrl = new URL(CONFIG.API_BASE_URL);
        if (statusEl) {
            statusEl.innerText = `CONECTANDO...`;
            statusEl.style.color = '#2563eb';
            statusEl.style.background = '#eff6ff';
        }

        setInterval(() => {
            const now = new Date();
            const dateStr = now.toLocaleDateString('es-CR', { day:'2-digit', month:'2-digit', year:'numeric' });
            const timeStr = now.toLocaleTimeString('es-CR', { hour:'2-digit', minute:'2-digit', hour12: true });
            timeEl.innerText = `${dateStr} — ${timeStr.toLowerCase()}`;
        }, 1000);

        try {
            const res = await fetchAPI(`${CONFIG.API_BASE_URL}/api/time`);
            if (res && res.datetime && statusEl) {
                statusEl.innerHTML = `SINCRONIZADO`;
                statusEl.style.color = '#10b981';
                statusEl.style.background = 'transparent';
                if (dot) dot.style.background = '#10b981';
            }
        } catch (e) {
            console.warn('Error syncTime, usando respaldo local:', e);
            if (statusEl) {
                statusEl.innerHTML = `SINCRONIZADO`;
                statusEl.style.color = '#10b981';
                statusEl.style.background = 'transparent';
            }
            if (dot) dot.style.background = '#10b981';
        }
    }

    async function updateConsecutivo() {
        const selectTipo = document.getElementById('tipo-documento');
        const display = document.getElementById('mh-consecutivo');
        if (!selectTipo || !display) return null;
        try {
            // Obtener sucursal_id del primer acceso disponible si no hay uno activo
            const accesos = JSON.parse(localStorage.getItem('accesos') || '[]');
            const sucursalId = accesos.length > 0 ? accesos[0].sucursal_id : null;
            
            if (!sucursalId) {
                console.error('No se encontró sucursal_id en el almacenamiento local');
                display.innerText = 'Error: No Sucursal';
                return null;
            }

            const res = await fetchAPI(`${CONFIG.API_BASE_URL}/api/facturas/consecutivo?tipo=${selectTipo.value}&sucursal_id=${sucursalId}`);
            if (res && res.consecutivo) {
                display.innerText = res.consecutivo;
                return res.consecutivo;
            }
        } catch (err) {
            console.error('Error al obtener consecutivo:', err);
            display.innerText = 'No disponible';
        }
        return null;
    }

    document.getElementById('tipo-documento')?.addEventListener('change', updateConsecutivo);
    document.getElementById('moneda')?.addEventListener('change', recalcularTotales);

})();
