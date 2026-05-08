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

    (function() {
        const input = document.getElementById('buscar-cliente-id');
        const dropdown = document.getElementById('cliente-dropdown');
        if (!input || !dropdown) return;
        function closeDropdown() { dropdown.style.display = 'none'; dropdown.innerHTML = ''; }
        input.addEventListener('input', async function() {
            const q = this.value.trim();
            if (q.length < 2) { closeDropdown(); return; }
            try {
                const matches = await fetchAPI(`${CONFIG.API_BASE_URL}/api/clientes?q=${encodeURIComponent(q)}`);
                dropdown.innerHTML = '';
                if (!matches || !matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8;">No se encontraron clientes</div>';
                } else {
                    matches.forEach(cliente => {
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.innerHTML = `<div><strong>${cliente.nombre}</strong><br><small>${cliente.identificacion}</small></div>`;
                        item.onclick = () => { window.seleccionarCliente(cliente); closeDropdown(); };
                        dropdown.appendChild(item);
                    });
                }
                dropdown.style.display = 'block';
            } catch (err) { console.error(err); }
        });
        window.seleccionarCliente = function(cliente) {
            const tiposTexto = {'01':'FÍSICA', '02':'JURÍDICA', '03':'DIMEX', '04':'NITE'};
            mostrarCliente({
                id: cliente.id, tipo_id: tiposTexto[cliente.tipo_id] || cliente.tipo_id, num_id: cliente.identificacion, nombre: cliente.nombre,
                nombre_comercial: cliente.nombre_comercial || cliente.nombre, provincia: cliente.provincia, canton: cliente.canton, distrito: cliente.distrito,
                otras_senas: cliente.direccion, telefono: cliente.telefono || cliente.movil, email: cliente.email || cliente.correo,
                actividad: cliente.actividad_economica || cliente.actividad, regimen: cliente.regimen || 'General'
            });
            input.value = cliente.identificacion;
            document.getElementById('cliente-info-panel').dataset.clientId = cliente.id;
        };
        document.getElementById('btn-buscar-cliente').onclick = async () => {
            const q = input.value.trim();
            if (!q) return;
            const matches = await fetchAPI(`${CONFIG.API_BASE_URL}/api/clientes?q=${encodeURIComponent(q)}`);
            if (matches && matches.length > 0) seleccionarCliente(matches[0]);
            else Swal.fire('Error', 'Cliente no encontrado', 'error');
        };
        document.getElementById('btn-limpiar-cliente').onclick = limpiarCliente;
        document.addEventListener('click', (e) => { if (e.target !== input) closeDropdown(); });
    })();

    (function() {
        const input = document.getElementById('buscar-cabys');
        const dropdown = document.getElementById('cabys-dropdown');
        if (!input || !dropdown) return;
        function closeDropdown() { dropdown.style.display = 'none'; dropdown.innerHTML = ''; }
        input.addEventListener('input', async function() {
            const q = this.value.trim();
            if (q.length < 2) { closeDropdown(); return; }
            try {
                const matches = await fetchAPI(`${CONFIG.API_BASE_URL}/api/productos?q=${encodeURIComponent(q)}`);
                dropdown.innerHTML = '';
                if (!matches || !matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8;">Sin resultados</div>';
                } else {
                    matches.forEach(prod => {
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.style.display = 'flex';
                        item.style.justifyContent = 'space-between';
                        item.innerHTML = `<div><strong>${prod.nombre || prod.descripcion}</strong><br><small>${prod.cabys || ''}</small></div><div style="font-weight:900; color:#1e40af;">₡${(prod.precio_venta || 0).toLocaleString()}</div>`;
                        item.onclick = () => { input.value = ''; closeDropdown(); agregarLineaProducto(prod); };
                        dropdown.appendChild(item);
                    });
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
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div style="font-weight:900;">#${lineIndex} - ${displayDetail}</div>
                <div style="display:flex; gap:8px;">
                    <button type="button" onclick="configurarExoneracion('${card.id}')" style="background:#fffcf0; border:1px solid #fbbf24; padding:5px 10px; border-radius:8px; font-size:0.7rem; font-weight:900;">EXO</button>
                    <button type="button" onclick="eliminarLinea('${card.id}')" style="background:#fff1f2; border:1px solid #fecdd3; color:#ef4444; width:30px; height:30px; border-radius:8px;">×</button>
                </div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;">
                <div><label style="font-size:0.6rem; color:#94a3b8;">CANT.</label><input type="number" class="item-qty" value="1" min="1" oninput="recalcularTotales()" style="width:100%; font-weight:900;"></div>
                <div><label style="font-size:0.6rem; color:#94a3b8;">DESC %</label><input type="number" class="item-desc-pct" value="0" min="0" oninput="validateDiscount(this); recalcularTotales()" style="width:100%; font-weight:900;"></div>
                <div><label style="font-size:0.6rem; color:#94a3b8;">IVA %</label><input type="number" class="item-tax-pct" value="${prod.impuesto || 13}" readonly style="width:100%; font-weight:900;"></div>
            </div>
            <div style="text-align:right; margin-top:10px;">
                <input type="hidden" class="item-detail" value="${displayDetail}">
                <span class="subtotal-cell" style="font-weight:950; color:#1e40af; font-size:1.4rem;">${symbol}0.00</span>
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
        currentRates = { usd: 512, eur: 554 };
        const elV = document.getElementById('fx-usd-venta'); if(elV) elV.textContent = '₡' + currentRates.usd;
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
            if (!consecutivo || consecutivo.includes("ERROR")) return Swal.fire('Error', 'Consecutivo no válido', 'error');

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
                window.location.reload();
            }
        } catch (err) { Swal.fire('Error', err.message || 'Error al emitir factura', 'error'); }
    });

    async function syncTime() {
        const timeEl = document.getElementById('realtime-date');
        if (!timeEl) return;
        setInterval(() => {
            timeEl.innerText = new Date().toLocaleString('es-CR');
        }, 1000);
    }

    async function updateConsecutivo() {
        const selectTipo = document.getElementById('tipo-documento');
        const display = document.getElementById('mh-consecutivo');
        if (!selectTipo || !display) return;
        try {
            const res = await fetchAPI(`${CONFIG.API_BASE_URL}/api/facturas/consecutivo?tipo=${selectTipo.value}`);
            if (res && res.consecutivo) {
                display.innerText = res.consecutivo;
            }
        } catch (err) { display.innerText = "ERROR"; }
    }

    document.getElementById('tipo-documento')?.addEventListener('change', updateConsecutivo);
    document.getElementById('moneda')?.addEventListener('change', recalcularTotales);

})();
