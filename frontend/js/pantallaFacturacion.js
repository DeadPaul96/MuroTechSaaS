(function () {
    // --- SELECTORES GLOBALES ---
    const ventaSection = document.getElementById('venta-section');
    const receptorAlert = document.getElementById('receptor-alert');
    const detailLinesContainer = document.getElementById('detalle-lineas');
    const draftSection = document.getElementById('section-drafts');
    
    // --- ESTADO ---
    let currentRates = { usd: 1, eur: 1 };
    const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };

    // --- HELPER DE BÚSQUEDA ---
    const fastMatch = (text, query) => {
        if (!query) return true;
        const words = query.toLowerCase().split(/\s+/).filter(w => w.length > 0);
        const target = (text || '').toLowerCase();
        return words.every(word => target.includes(word));
    };

    // --- INICIALIZACIÓN ---
    document.addEventListener('DOMContentLoaded', () => {
        syncRates();
        checkDraft();
        toggleVentaSection(false); // Bloqueado por defecto
        
        // Prevenir envío con Enter (excepto en áreas de texto o botones)
        document.getElementById('factura-form')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
            }
        });
    });

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

    // --- LÓGICA DE CLIENTES ---
    window.mostrarCliente = function(data) {
        document.getElementById('cli-tipo-id').textContent     = data.tipoId;
        document.getElementById('cli-num-id').textContent      = data.numId;
        document.getElementById('cli-nombre').textContent      = data.nombre;
        document.getElementById('cli-nombre-com').textContent  = data.nombreCom;
        document.getElementById('cli-provincia').textContent   = data.provincia;
        document.getElementById('cli-canton').textContent      = data.canton;
        document.getElementById('cli-distrito').textContent    = data.distrito;
        document.getElementById('cli-otras-senas').textContent = data.otrasSenas;
        document.getElementById('cli-telefono').textContent    = data.telefono;
        document.getElementById('cli-email').textContent       = data.email;
        document.getElementById('cli-actividad').textContent   = data.actividad;
        document.getElementById('cli-regimen').textContent     = data.regimen;
        document.getElementById('cliente-info-panel').classList.add('visible');
        toggleVentaSection(true);
        saveDraft();
    };

    window.limpiarCliente = function() {
        const ids = ['cli-tipo-id','cli-num-id','cli-nombre','cli-nombre-com',
                     'cli-provincia','cli-canton','cli-distrito','cli-otras-senas',
                     'cli-telefono','cli-email','cli-actividad','cli-regimen'];
        ids.forEach(id => document.getElementById(id).textContent = '–');
        document.getElementById('cliente-info-panel').classList.remove('visible');
        document.getElementById('buscar-cliente-id').value = '';
        toggleVentaSection(false);
        saveDraft();
    };

    // --- AUTOCOMPLETE CLIENTES ---
    (function() {
        const input = document.getElementById('buscar-cliente-id');
        const dropdown = document.getElementById('cliente-dropdown');
        if (!input || !dropdown) return;

        function closeDropdown() { dropdown.style.display = 'none'; dropdown.innerHTML = ''; }

        input.addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            if (q.length < 1) { closeDropdown(); return; }
            const db = window.muroDB;
            if (!db) return;
            const matches = db.getClientes().filter(c => 
                fastMatch(`${c.nombre} ${c.identificacion} ${c.correo || ''}`, q)
            ).slice(0, 8);
            
            dropdown.innerHTML = '';
            if (!matches.length) {
                dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron clientes</div>';
            } else {
                matches.forEach(cliente => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `<div><strong>${cliente.nombre}</strong><br><small>${cliente.identificacion}</small></div>`;
                    item.onclick = () => { seleccionarCliente(cliente); closeDropdown(); };
                    dropdown.appendChild(item);
                });
            }
            dropdown.style.display = 'block';
        });

        function seleccionarCliente(cliente) {
            const tiposTexto = {'01':'01 – Física', '02':'02 – Jurídica', '03':'03 – DIMEX', '04':'04 – NITE'};
            mostrarCliente({
                tipoId: tiposTexto[cliente.tipoId] || cliente.tipoId,
                numId: cliente.identificacion,
                nombre: cliente.nombre,
                nombreCom: cliente.nombre,
                provincia: cliente.provincia || '—',
                canton: cliente.canton || '—',
                distrito: cliente.distrito || '—',
                otrasSenas: cliente.direccion || '—',
                telefono: cliente.telefono || cliente.movil || '—',
                email: cliente.correo || '—',
                actividad: 'Actividad Hacienda',
                regimen: cliente.regimen || 'General'
            });
            input.value = cliente.identificacion;
        }

        document.getElementById('btn-buscar-cliente').onclick = () => {
            const q = input.value.trim().toLowerCase();
            if (!q) return;
            const found = window.muroDB?.getClientes().find(c => c.identificacion.includes(q) || c.nombre.toLowerCase().includes(q));
            if (found) seleccionarCliente(found);
            else Swal.fire('Error', 'Cliente no encontrado', 'error');
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

        input.addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            if (q.length < 1) { closeDropdown(); return; }
            const db = window.muroDB;
            if (!db) return;
            
            const matches = db.getProductos().filter(p => 
                fastMatch(`${p.nombre || ''} ${p.descripcion || ''} ${p.marca || ''} ${p.modelo || ''} ${p.caracteristicas || ''} ${p.cabys || ''} ${p.codigo || ''}`, q)
            ).slice(0, 10);

            dropdown.innerHTML = '';
            if (!matches.length) {
                dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">Sin resultados</div>';
            } else {
                matches.forEach(prod => {
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
                    item.onclick = () => { agregarLineaProducto(prod); input.value = ''; closeDropdown(); };
                    dropdown.appendChild(item);
                });
            }
            dropdown.style.display = 'block';
        });
        document.addEventListener('click', (e) => { if (e.target !== input) closeDropdown(); });
    })();

    // --- GESTIÓN DE LÍNEAS (ESTILO CARD) ---
    window.agregarLineaProducto = function(prod) {
        const empty = document.getElementById('empty-row');
        if (empty) empty.remove();

        const lineIndex = detailLinesContainer.querySelectorAll('.item-card').length + 1;
        const moneda = document.getElementById('moneda').value;
        const symbol = monedaSymbols[moneda] || '$';
        const displayDetail = [prod.marca, prod.modelo, prod.caracteristicas].filter(Boolean).join(' ').trim() || (prod.nombre || prod.descripcion);
        
        let precioRef = prod.precioVenta || prod.precio || 0;
        // Ajustar según moneda seleccionada si la base es CRC
        if (moneda === 'USD') precioRef /= currentRates.usd;
        if (moneda === 'EUR') precioRef /= currentRates.eur;

        const card = document.createElement('div');
        card.id = 'linea-' + Date.now();
        card.className = 'item-card';
        card.dataset.precioOriginal = precioRef;
        card.dataset.descMax = prod.descuentoMaximo || 100;

        card.setAttribute('style', `
            background: white; border: 1.5px solid #edf2f7; border-radius: 18px; padding: 16px;
            display: flex; flex-direction: column; gap: 12px; position: relative;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02); width: 100%; box-sizing: border-box;
        `);

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="background:#2563eb; color:white; font-size:0.7rem; font-weight:900; padding:3px 8px; border-radius:8px;">#${lineIndex}</span>
                    <div style="font-weight:900; font-size:1.1rem; color:#1e293b;">${displayDetail}</div>
                </div>
                <button type="button" onclick="eliminarLinea('${card.id}')" style="background:#fef2f2; border:none; color:#ef4444; width:34px; height:34px; border-radius:10px; cursor:pointer; display:flex; align-items:center; justify-content:center;">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
            <div style="display:flex; flex-direction:column; gap:4px;">
                <div style="display:flex; gap:10px;">
                    <span style="font-size:0.65rem; font-weight:800; color:#64748b; background:#f1f5f9; padding:2px 6px; border-radius:4px;">SKU: ${prod.codigoInterno || prod.codigo || '—'}</span>
                    <span style="font-size:0.65rem; font-weight:800; color:#64748b; background:#f1f5f9; padding:2px 6px; border-radius:4px;">CABYS: ${prod.cabys || '—'}</span>
                </div>
                <div style="font-size:0.75rem; color:#94a3b8; font-weight:600;">${prod.nombre || prod.descripcion}</div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end; border-top:1px solid #f1f5f9; padding-top:10px;">
                <div style="display:flex; gap:15px; align-items:center;">
                    <div>
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase;">Cant.</label>
                        <input type="number" class="item-qty" value="1" min="1" step="1" oninput="this.value=Math.max(1,Math.floor(this.value)); recalcularTotales();" style="width:35px; border:1px solid #e2e8f0; border-radius:6px; padding:3px; font-weight:900; text-align:center;">
                    </div>
                    <div>
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase;">Desc %</label>
                        <input type="number" class="item-desc-pct" value="0" min="0" max="100" oninput="this.value=Math.max(0,Math.floor(this.value)); validateDiscount(this); recalcularTotales();" style="width:35px; border:1px solid #fecdd3; border-radius:6px; padding:3px; font-weight:900; background:#fff1f2; color:#e11d48; text-align:center;">
                    </div>
                    <div>
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase;">IVA %</label>
                        <input type="number" class="item-tax-pct" value="${prod.impuesto || 13}" readonly style="width:30px; border:none; background:transparent; font-weight:900; color:#10b981;">
                    </div>
                    <button type="button" onclick="configurarExoneracion('${card.id}')" style="background:#fffcf0; border:1px solid #fbbf24; color:#d97706; padding:3px 10px; border-radius:8px; font-size:0.65rem; font-weight:900; cursor:pointer;">EXO</button>
                    <input type="hidden" class="item-tax-type" value="01">
                    <input type="hidden" class="item-detail" value="${displayDetail}">
                    <input type="hidden" class="item-desc" value="${prod.nombre || prod.descripcion}">
                    <input type="hidden" class="item-cabys" value="${prod.cabys || ''}">
                    <input type="hidden" class="item-sku" value="${prod.codigoInterno || prod.codigo || ''}">
                </div>
                <div style="text-align:right;">
                    <div style="font-size:0.6rem; color:#94a3b8; font-weight:800; text-transform:uppercase;">Subtotal</div>
                    <div class="subtotal-cell" style="font-weight:900; color:#1e40af; font-size:1.3rem;">${symbol}0.00</div>
                </div>
            </div>
        `;
        detailLinesContainer.appendChild(card);
        recalcularTotales();
    };

    window.eliminarLinea = function(id) {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
            if (detailLinesContainer.querySelectorAll('.item-card').length === 0) {
                detailLinesContainer.innerHTML = `<div id="empty-row" style="text-align:center; padding:50px 20px; color:#94a3b8; background:#fff; border:2px dashed #e2e8f0; border-radius:16px;">
                    <div style="font-weight:800;">No hay productos en la lista</div>
                </div>`;
            }
            recalcularTotales();
        }
    };

    window.recalcularTotales = function() {
        let subtotalTotal = 0;
        let descTotal = 0;
        let taxTotal = 0;
        const moneda = document.getElementById('moneda').value;
        const symbol = monedaSymbols[moneda] || '$';

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

            if (exoData && exoData.pct > 0) {
                tax -= (tax * (exoData.pct / 100));
            }

            const lineaTotal = neto + tax;
            card.querySelector('.subtotal-cell').textContent = symbol + lineaTotal.toLocaleString('es-CR', {minimumFractionDigits:2});
            
            subtotalTotal += base;
            descTotal += desc;
            taxTotal += tax;
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

    window.validateDiscount = function(input) {
        const card = input.closest('.item-card');
        const max = parseFloat(card.dataset.descMax) || 100;
        if (parseFloat(input.value) > max) {
            Swal.fire('Atención', `Límite de descuento: ${max}%`, 'warning');
            input.value = max;
        }
    };

    // --- DRAFTS ---
    function saveDraft() {
        const data = {
            receptorId: document.getElementById('cli-num-id').textContent,
            moneda: document.getElementById('moneda').value,
            lineas: []
        };
        document.querySelectorAll('.item-card').forEach(card => {
            data.lineas.push({
                precio: card.dataset.precioOriginal,
                descMax: card.dataset.descMax,
                qty: card.querySelector('.item-qty').value,
                descPct: card.querySelector('.item-desc-pct').value,
                taxPct: card.querySelector('.item-tax-pct').value,
                detail: card.querySelector('.item-detail').value,
                descrip: card.querySelector('.item-desc').value,
                cabys: card.querySelector('.item-cabys').value,
                sku: card.querySelector('.item-sku').value
            });
        });
        if (data.lineas.length > 0) localStorage.setItem('muro_draft_factura', JSON.stringify(data));
    }

    function checkDraft() {
        if (localStorage.getItem('muro_draft_factura')) {
            if (draftSection) draftSection.style.display = 'block';
        }
    }

    // --- DIVISAS ---
    async function syncRates() {
        try {
            const res = await fetch("https://api.hacienda.go.cr/indicadores/tc");
            if (!res.ok) return;
            const data = await res.json();
            if (data.dolar) {
                currentRates.usd = data.dolar.venta.valor;
                document.getElementById('fx-usd-venta').textContent = '₡' + currentRates.usd;
                document.getElementById('fx-usd-fecha').textContent = data.dolar.venta.fecha.split('-').reverse().join('/');
            }
            if (data.euro) {
                currentRates.eur = data.euro.colones;
                document.getElementById('fx-eur-valor').textContent = '₡' + currentRates.eur;
                document.getElementById('fx-eur-fecha').textContent = data.euro.fecha.split('-').reverse().join('/');
            }
        } catch (e) { console.warn("Sync TC failed"); }
    }

    // --- EXONERACIONES ---
    window.configurarExoneracion = function(cardId) {
        const card = document.getElementById(cardId);
        const current = card.dataset.exoneracion ? JSON.parse(card.dataset.exoneracion) : { pct: 100, num: '' };

        Swal.fire({
            title: 'Configurar Exoneración',
            html: `
                <input id="exo-num" class="swal2-input" placeholder="Num. Documento" value="${current.num}">
                <input id="exo-pct" type="number" class="swal2-input" placeholder="% Exoneración" value="${current.pct}">
            `,
            showCancelButton: true,
            confirmButtonText: 'Aplicar'
        }).then(res => {
            if (res.isConfirmed) {
                card.dataset.exoneracion = JSON.stringify({
                    num: document.getElementById('exo-num').value,
                    pct: parseFloat(document.getElementById('exo-pct').value) || 0
                });
                recalcularTotales();
            }
        });
    };

    // --- EMITIR ---
    document.getElementById('factura-form')?.addEventListener('submit', function(e) {
        e.preventDefault();
        const receptorId = document.getElementById('cli-num-id').textContent;
        if (receptorId === '–') return Swal.fire('Error', 'Debe seleccionar un cliente', 'error');
        
        if (detailLinesContainer.querySelectorAll('.item-card').length === 0) {
            return Swal.fire('Error', 'El detalle está vacío', 'error');
        }

        Swal.fire({
            title: 'Procesando...',
            text: 'Enviando a Hacienda v4.4',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        setTimeout(() => {
            localStorage.removeItem('muro_draft_factura');
            Swal.fire('¡Éxito!', 'Factura emitida correctamente.', 'success').then(() => location.reload());
        }, 2000);
    });

})();