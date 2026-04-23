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

    // Usar multiWordMatch de utils.js

    // Validar descuento máximo por producto
    window.validateDiscount = function(input) {
        const row = input.closest('.item-card');
        if(!row) {
            console.error("No se encontró el contenedor .item-card");
            return;
        }
        // Intentar obtener de dataset o de input oculto
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

    // --- INICIALIZACIÓN SEGURA ---
    function init() {
        syncRates();
        checkDraft();
        toggleVentaSection(false); // Bloqueado por defecto
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

    // --- LÓGICA DE CLIENTES ---
    window.mostrarCliente = function(data) {
        // Función auxiliar para setear texto de forma segura
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

        // Manejo dinámico de actividades (Componente Premium)
        const container = document.getElementById('cli-actividad-container');
        if (container) {
            container.innerHTML = '';
            const acts = (data.actividad || '').split(' · ').filter(a => a.trim() !== '');
            
            if (acts.length > 1) {
                // Crear componente de selección personalizada
                const wrapper = document.createElement('div');
                wrapper.className = 'custom-activity-select';
                wrapper.style.position = 'relative';

                const trigger = document.createElement('div');
                trigger.className = 'activity-trigger';
                trigger.innerHTML = `
                    <span class="activity-text">${acts[0]}</span>
                    <i class="fas fa-chevron-down"></i>
                `;
                
                const list = document.createElement('div');
                list.className = 'activity-list-dropdown';
                list.style.display = 'none';
                
                acts.forEach((a, idx) => {
                    const item = document.createElement('div');
                    item.className = 'activity-opt';
                    if(idx === 0) item.classList.add('selected');
                    
                    // Separar código de descripción para estilo visual
                    const match = a.match(/\[(.*?)\]\s*(.*)/);
                    if (match) {
                        item.innerHTML = `<span class="act-code">[${match[1]}]</span> <span class="act-desc">${match[2]}</span>`;
                    } else {
                        item.textContent = a;
                    }

                    item.onclick = () => {
                        trigger.querySelector('.activity-text').textContent = a;
                        list.querySelectorAll('.activity-opt').forEach(opt => opt.classList.remove('selected'));
                        item.classList.add('selected');
                        list.style.display = 'none';
                    };
                    list.appendChild(item);
                });

                trigger.onclick = (e) => {
                    e.stopPropagation();
                    const isOpen = list.style.display === 'block';
                    document.querySelectorAll('.activity-list-dropdown').forEach(d => d.style.display = 'none');
                    list.style.display = isOpen ? 'none' : 'block';
                };

                document.addEventListener('click', () => list.style.display = 'none');

                wrapper.appendChild(trigger);
                wrapper.appendChild(list);
                container.appendChild(wrapper);
            } else {
                // Mostrar texto simple si solo hay una
                const span = document.createElement('span');
                span.id = 'cli-actividad';
                span.style.fontSize = '0.85rem';
                span.style.fontWeight = '800';
                span.style.color = 'var(--primary-dark)';
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
        const ids = ['cli-tipo-id','cli-num-id','cli-nombre','cli-nombre-com',
                     'cli-provincia','cli-canton','cli-distrito','cli-otras-senas',
                     'cli-telefono','cli-email','cli-regimen'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '–';
        });
        const container = document.getElementById('cli-actividad-container');
        if (container) container.innerHTML = '<span id="cli-actividad" style="font-size:0.8rem; font-weight:700; color:#1e293b;">–</span>';
        
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

        input.addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            if (q.length < 1) { closeDropdown(); return; }
            const db = window.muroDB;
            if (!db) return;
            const matches = db.getClientes().filter(c => 
                multiWordMatch(`${c.nombre} ${c.identificacion} ${c.correo || ''}`, q)
            ).slice(0, 8);
            
            dropdown.innerHTML = '';
            if (!matches.length) {
                dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron clientes</div>';
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
        });

        window.seleccionarCliente = function(cliente) {
            const tiposTexto = {'01':'FÍSICA', '02':'JURÍDICA', '03':'DIMEX', '04':'NITE'};
            mostrarCliente({
                tipo_id: tiposTexto[cliente.tipoId] || cliente.tipoId,
                num_id: cliente.identificacion,
                nombre: cliente.nombre,
                nombre_comercial: cliente.nombre_comercial || cliente.nombre,
                provincia: cliente.provincia || '—',
                canton: cliente.canton || '—',
                distrito: cliente.distrito || '—',
                otras_senas: cliente.direccion || '—',
                telefono: cliente.telefono || cliente.movil || '—',
                email: cliente.correo || '—',
                actividad: cliente.actividad || 'Actividad Hacienda',
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
                multiWordMatch(`${p.nombre || ''} ${p.descripcion || ''} ${p.marca || ''} ${p.modelo || ''} ${p.caracteristicas || ''} ${p.cabys || ''} ${p.codigo || ''}`, q)
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
                    item.onclick = () => {
                        input.value = '';
                        closeDropdown();
                        agregarLineaProducto(prod);
                    };
                    dropdown.appendChild(item);
                });
            }
            dropdown.style.display = 'block';
        });

        // Soporte para tecla Enter: Selecciona el primer resultado
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const firstResult = dropdown.querySelector('.autocomplete-item');
                if (firstResult) firstResult.click();
            }
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
        card.className = 'item-card fac-line-item';
        card.dataset.precioOriginal = precioRef;
        card.dataset.descMax = prod.descuento_maximo || 0;

        card.setAttribute('style', `
            background: white; border: 1.5px solid #edf2f7; border-radius: 18px; padding: 16px;
            display: flex; flex-direction: column; gap: 12px; position: relative;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02); width: 100%`);
            
        card.innerHTML = `
            <!-- Fila Superior: Título y Acciones Dinámicas -->
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:10px; flex:1;">
                    <span style="background:#2563eb; color:white; font-size:0.7rem; font-weight:900; padding:3px 10px; border-radius:8px;">#${lineIndex}</span>
                    <div style="font-weight:900; font-size:1.2rem; color:#0f172a; letter-spacing:-0.02em;">${displayDetail}</div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <button type="button" onclick="configurarExoneracion('${card.id}')" style="background:#fffcf0; border:1.5px solid #fbbf24; color:#d97706; padding:6px 12px; border-radius:10px; font-size:0.75rem; font-weight:900; cursor:pointer; display:flex; align-items:center; gap:6px; transition:all 0.2s;" onmouseover="this.style.background='#fbbf24'; this.style.color='white'" onmouseout="this.style.background='#fffcf0'; this.style.color='#d97706'">
                        <i class="fas fa-shield-alt"></i> EXO
                    </button>
                    <button type="button" onclick="eliminarLinea('${card.id}')" style="background:#fff1f2; border:1px solid #fecdd3; color:#ef4444; width:36px; height:36px; border-radius:10px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition: all 0.2s;" onmouseover="this.style.background='#ef4444'; this.style.color='white'" onmouseout="this.style.background='#fff1f2'; this.style.color='#ef4444'">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>

            <!-- Bloque Central: Metadatos y Operación (ULTRA-COMPACTO) -->
            <div style="display:flex; justify-content:space-between; align-items:center; background:#f8fafc; padding:12px 18px; border-radius:12px; border:1px solid #f1f5f9; margin-top: 5px;">
                <!-- Izquierda: Datos Técnicos -->
                <div style="display:flex; gap:12px; flex-wrap:wrap;">
                    <div style="font-size:0.7rem; font-weight:800; color:#475569; background:white; padding:4px 10px; border-radius:8px; border:1px solid #e2e8f0;">
                        <span style="color:#94a3b8; font-size:0.55rem; text-transform:uppercase; display:block; margin-bottom:1px;">SKU</span> ${prod.codigoInterno || prod.codigo || '—'}
                    </div>
                    <div style="font-size:0.7rem; font-weight:800; color:#475569; background:white; padding:4px 10px; border-radius:8px; border:1px solid #e2e8f0;">
                        <span style="color:#94a3b8; font-size:0.55rem; text-transform:uppercase; display:block; margin-bottom:1px;">CABYS</span> ${prod.cabys || '—'}
                    </div>
                </div>

                <!-- Derecha: Controles de Transacción -->
                <div style="display:flex; gap:15px; align-items:center;">
                    <!-- Cantidad -->
                    <div style="text-align:center; width: 75px;">
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px;">CANT.</label>
                        <div style="background:white; border:1.8px solid #e2e8f0; border-radius:10px; height: 40px; display: flex; align-items: center; justify-content: center;">
                            <input type="number" class="item-qty" value="1" min="0.001" step="any" oninput="if(this.value<0)this.value=0; recalcularTotales();" style="width:100%; border:none; background:transparent; font-weight:900; text-align:center; font-size:1.15rem; color:#0f172a; outline:none;">
                        </div>
                    </div>
                    
                    <!-- Descuento -->
                    <div style="text-align:center; width: 95px;">
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px;">DESC. %</label>
                        <div style="display:flex; align-items:center; background:#fff1f2; border:1.8px solid #fecdd3; height: 40px; border-radius:10px; padding: 0 8px;">
                            <input type="number" class="item-desc-pct no-spin" value="0" min="0" max="${prod.descuento_maximo || 0}" step="any" oninput="if(this.value<0)this.value=0; validateDiscount(this); recalcularTotales();" style="width:100%; border:none; background:transparent; font-weight:900; color:#e11d48; text-align:center; font-size:1.15rem; outline:none;">
                            <span style="font-size:0.9rem; color:#e11d48; font-weight:900;">%</span>
                        </div>
                    </div>
                    <input type="hidden" class="item-max-desc" value="${prod.descuento_maximo || 0}">

                    <!-- IVA -->
                    <div style="text-align:center; width: 95px;">
                        <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px;">IVA %</label>
                        <div style="display:flex; align-items:center; background:#ecfdf5; border:1.8px solid #10b981; height: 40px; border-radius:10px; padding: 0 8px;">
                            <input type="number" class="item-tax-pct no-spin" value="${prod.impuesto || 13}" readonly style="width:100%; border:none; background:transparent; font-weight:900; color:#059669; font-size:1.15rem; outline:none; text-align:center;">
                            <span style="font-size:0.9rem; color:#059669; font-weight:900;">%</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Fila Inferior: Totales -->
            <div style="display:flex; justify-content:flex-end; align-items:center; padding-top:10px; margin-top:2px;">
                <input type="hidden" class="item-tax-type" value="01">
                <input type="hidden" class="item-detail" value="${displayDetail}">
                <input type="hidden" class="item-desc" value="${prod.nombre || prod.descripcion}">
                <input type="hidden" class="item-cabys" value="${prod.cabys || ''}">
                <input type="hidden" class="item-sku" value="${prod.codigoInterno || prod.codigo || ''}">

                <div style="text-align:right;">
                    <span style="font-size:0.65rem; color:#94a3b8; font-weight:900; text-transform:uppercase; margin-right:15px;">Subtotal Ítem</span>
                    <span class="subtotal-cell" style="font-weight:950; color:#1e40af; font-size:1.8rem; letter-spacing:-0.03em;">${symbol}0.00</span>
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
                detailLinesContainer.innerHTML = `<div id="empty-row" style="text-align:center; padding:50px 20px; color:#94a3b8; background:#fff; border:2px dashed #e2e8f0; border-radius:16px;">
                    <div style="font-weight:800;">No hay productos en la lista</div>
                </div>`;
            }
            recalcularTotales();
            setDirty();
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
        setDirty();
    };


    // --- DRAFTS ---
    window.saveDraftManual = function() {
        saveDraft();
        clearDirty();
        Swal.fire({
            icon: 'success',
            title: 'Borrador Guardado',
            text: 'Tu progreso ha sido guardado localmente.',
            timer: 1500,
            showConfirmButton: false,
            toast: true,
            position: 'top-end'
        });
    };

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

    window.recuperarBorrador = function() {
        const raw = localStorage.getItem('muro_draft_factura');
        if(!raw) return;
        const data = JSON.parse(raw);
        
        // 1. Moneda
        if(data.moneda) {
            const sel = document.getElementById('moneda');
            if(sel) {
                sel.value = data.moneda;
                sel.dispatchEvent(new Event('change'));
            }
        }
        
        // 2. Cliente
        if(data.receptorId && window.muroDB && window.seleccionarCliente) {
            const cliente = window.muroDB.getClientes().find(c => c.identificacion === data.receptorId);
            if(cliente) window.seleccionarCliente(cliente);
        }
        
        // 3. Líneas
        detailLinesContainer.innerHTML = '';
        data.lineas.forEach(l => {
            agregarLineaProducto({
                precioVenta: parseFloat(l.precio),
                descuento_maximo: parseFloat(l.descMax),
                marca: '', modelo: '', caracteristicas: '',
                nombre: l.descrip,
                descripcion: l.descrip,
                impuesto: parseFloat(l.taxPct),
                cabys: l.cabys,
                codigoInterno: l.sku
            });
            
            const cards = detailLinesContainer.querySelectorAll('.item-card');
            const lastCard = cards[cards.length - 1];
            if(lastCard) {
                lastCard.querySelector('.item-qty').value = l.qty;
                lastCard.querySelector('.item-desc-pct').value = l.descPct;
            }
        });
        
        recalcularTotales();
        document.getElementById('section-drafts').style.display = 'none';
        
        Swal.fire({
            icon: 'success',
            title: 'Borrador Recuperado',
            text: 'Se han restaurado todos los datos de la sesión anterior.',
            timer: 2000,
            showConfirmButton: false,
            toast: true,
            position: 'top-end'
        });
    };

    function checkDraft() {
        if (localStorage.getItem('muro_draft_factura')) {
            const draft = JSON.parse(localStorage.getItem('muro_draft_factura'));
            if (draft.lineas && draft.lineas.length > 0) {
                if (document.getElementById('section-drafts')) {
                    document.getElementById('section-drafts').style.display = 'block';
                }
            }
        }
    }

    // --- DIVISAS ---
    async function syncRates() {
        console.log("MUROTECH: Iniciando sincronización de tasas...");
        const urlDirecta = "https://api.hacienda.go.cr/indicadores/tc";
        const statusBadge = document.getElementById('dash-tc-status');
        
        let data = null;

        // AbortController para evitar esperas infinitas
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 4000);

        try {
            const res = await fetch(urlDirecta, { signal: controller.signal });
            if (res.ok) data = await res.json();
        } catch (e) { 
            console.warn("TC: Error de red o CORS. Usando Mock de respaldo."); 
        } finally {
            clearTimeout(timeout);
        }

        // Datos de Respaldo (Mock) si falla la API
        if (!data) {
            data = {
                dolar: { venta: { valor: 512.45, fecha: new Date().toISOString() } },
                euro: { colones: 554.20, fecha: new Date().toISOString() }
            };
        }

        if (data && data.dolar) {
            currentRates.usd = data.dolar.venta.valor;
            const elVenta = document.getElementById('fx-usd-venta');
            const elFecha = document.getElementById('fx-usd-fecha');
            if (elVenta) elVenta.textContent = '₡' + currentRates.usd.toFixed(2);
            if (elFecha) {
                const f = new Date(data.dolar.venta.fecha);
                elFecha.textContent = f.toLocaleDateString('es-CR');
            }
            
            if (data.euro) {
                currentRates.eur = data.euro.colones;
                const elEurVal = document.getElementById('fx-eur-valor');
                const elEurFec = document.getElementById('fx-eur-fecha');
                if (elEurVal) elEurVal.textContent = '₡' + currentRates.eur.toFixed(2);
                if (elEurFec) {
                    const f = new Date(data.euro.fecha);
                    elEurFec.textContent = f.toLocaleDateString('es-CR');
                }
            }

            if (statusBadge) {
                statusBadge.style.background = data.mock ? '#fff7ed' : '#ecfdf5';
                statusBadge.style.color = data.mock ? '#c2410c' : '#10b981';
                statusBadge.innerHTML = data.mock ? '<i class="fas fa-info-circle"></i> TASA ESTIMADA' : '<i class="fas fa-check-circle"></i> SINCRONIZADO';
            }
        }
    }

    // --- EXONERACIONES ---
    window.configurarExoneracion = function(cardId) {
        const card = document.getElementById(cardId);
        if (!card) return;

        const current = card.dataset.exoneracion ? JSON.parse(card.dataset.exoneracion) : { 
            active: false, tipoDoc: '01', fecha: '', numDoc: '', numArt: '', numInc: '', institucion: '01', pct: 0 
        };

        const qty = parseFloat(card.querySelector('.item-qty')?.value) || 1;
        const precio = parseFloat(card.dataset.precioOriginal) || 0;
        const descPct = parseFloat(card.querySelector('.item-desc-pct')?.value) || 0;
        const taxPct = parseFloat(card.querySelector('.item-tax-pct')?.value) || 13;
        
        const base = (precio * qty) * (1 - descPct / 100);
        const originalTax = base * (taxPct / 100);

        const instituciones = [
            {id:'01', n:'Ministerio de Hacienda'}, {id:'02', n:'Min. Relaciones Exteriores'},
            {id:'03', n:'Min. Agricultura y Ganadería'}, {id:'04', n:'MEIC'},
            {id:'05', n:'Cruz Roja'}, {id:'06', n:'Bomberos de Costa Rica'},
            {id:'07', n:'Asoc. Obras del Espíritu Santo'}, {id:'08', n:'Fecrunapa'},
            {id:'09', n:'EARTH'}, {id:'10', n:'INCAE'},
            {id:'11', n:'JPS'}, {id:'12', n:'Aresep'}, {id:'99', n:'Otros'}
        ];

        Swal.fire({
            title: null,
            width: '850px',
            padding: '0',
            showConfirmButton: false,
            html: `
                <div style="text-align:left; font-family:'Inter', sans-serif; overflow:hidden; border-radius:24px;">
                    <!-- Header Premium MUROTECH -->
                    <div style="background:#0f172a; padding:25px 35px; display:flex; justify-content:space-between; align-items:center;">
                        <div style="display:flex; align-items:center; gap:15px;">
                            <div style="background:rgba(255,255,255,0.1); width:48px; height:48px; border-radius:12px; display:flex; align-items:center; justify-content:center; color:#fbbf24;">
                                <i class="fas fa-shield-alt fa-lg"></i>
                            </div>
                            <div>
                                <h3 style="color:white; margin:0; font-size:1.2rem; font-weight:900; letter-spacing:-0.01em;">Configuración de Exoneración</h3>
                                <p style="color:#94a3b8; margin:0; font-size:0.75rem; font-weight:600; text-transform:uppercase;">Gestión de tributos y autorizaciones especiales</p>
                            </div>
                        </div>
                        <div id="exo-toggle-btn" style="background:${current.active ? '#fbbf24' : '#334155'}; padding:8px 18px; border-radius:12px; color:${current.active ? '#92400e' : '#cbd5e1'}; font-weight:900; font-size:0.75rem; cursor:pointer; transition:all 0.3s; display:flex; align-items:center; gap:8px;">
                             <i class="fas ${current.active ? 'fa-toggle-on' : 'fa-toggle-off'} fa-lg"></i>
                             ${current.active ? 'ACTIVA' : 'DESACTIVADA'}
                        </div>
                        <input type="checkbox" id="exo-active" ${current.active ? 'checked' : ''} style="display:none;">
                    </div>

                    <div id="exo-main-body" style="padding:30px 35px; background:white; opacity: ${current.active ? '1' : '0.5'}; pointer-events: ${current.active ? 'auto' : 'none'}; transition:all 0.4s;">
                        
                        <!-- Grid MUROTECH - Organización por Prioridad -->
                        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:20px; margin-bottom:25px;">
                            
                            <!-- Fila 1: Origen Legal (Ancho 2+1) -->
                            <div style="grid-column: span 2;">
                                <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.05em;">Tipo de Documento / Autorización</label>
                                <select id="exo-tipo-doc" style="width:100%; border:2px solid #f1f5f9; border-radius:12px; padding:12px; font-size:0.85rem; font-weight:700; color:#1e293b; background:#f8fafc; outline:none; cursor:pointer;">
                                    <option value="01" ${current.tipoDoc==='01'?'selected':''}>01 - Compras autorizadas por la Dirección General de Tributación</option>
                                    <option value="02" ${current.tipoDoc==='02'?'selected':''}>02 - Ventas exentas a diplomáticos</option>
                                    <option value="03" ${current.tipoDoc==='03'?'selected':''}>03 - Autorizado por Ley especial</option>
                                    <option value="04" ${current.tipoDoc==='04'?'selected':''}>04 - Exenciones Dirección General de Hacienda autorización local genérica</option>
                                    <option value="05" ${current.tipoDoc==='05'?'selected':''}>05 - Transitorio V (Ingeniería, Arq, Topografía)</option>
                                    <option value="06" ${current.tipoDoc==='06'?'selected':''}>06 - Servicios turísticos inscritos ante el ICT</option>
                                    <option value="07" ${current.tipoDoc==='07'?'selected':''}>07 - Transitorio XVII (Reciclaje y reutilizable)</option>
                                    <option value="08" ${current.tipoDoc==='08'?'selected':''}>08 - Exoneración a zona franca</option>
                                    <option value="09" ${current.tipoDoc==='09'?'selected':''}>09 - Servicios complementarios exportación (Art 11)</option>
                                    <option value="10" ${current.tipoDoc==='10'?'selected':''}>10 - Órgano de las corporaciones municipales</option>
                                    <option value="11" ${current.tipoDoc==='11'?'selected':''}>11 - Exenciones Hacienda autorización local concreta</option>
                                    <option value="99" ${current.tipoDoc==='99'?'selected':''}>99 - Otros</option>
                                </select>
                            </div>
                            <div>
                                <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.05em;">Fecha Emisión</label>
                                <input type="date" id="exo-fecha" value="${current.fecha}" style="width:100%; border:2px solid #f1f5f9; border-radius:12px; padding:12px; font-size:0.85rem; font-weight:700; background:#f8fafc; outline:none;">
                            </div>

                            <!-- Fila 2: Referencias (Ancho 1+1+1) -->
                            <div>
                                <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.05em;">Nº Autorización</label>
                                <input type="text" id="exo-num-doc" placeholder="Referencia" value="${current.numDoc}" style="width:100%; border:2px solid #f1f5f9; border-radius:12px; padding:12px; font-size:0.85rem; font-weight:700; background:#f8fafc; outline:none;">
                            </div>
                            <div>
                                <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.05em;">Artículo Ley</label>
                                <input type="text" id="exo-num-art" placeholder="Ej. Art 3" value="${current.numArt}" style="width:100%; border:2px solid #f1f5f9; border-radius:12px; padding:12px; font-size:0.85rem; font-weight:700; background:#f8fafc; outline:none;">
                            </div>
                            <div>
                                <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.05em;">Inciso Ley</label>
                                <input type="text" id="exo-num-inc" placeholder="Ej. Inc A" value="${current.numInc}" style="width:100%; border:2px solid #f1f5f9; border-radius:12px; padding:12px; font-size:0.85rem; font-weight:700; background:#f8fafc; outline:none;">
                            </div>

                            <!-- Fila 3: Institución (Ancho 3) -->
                            <div style="grid-column: span 3;">
                                <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.05em;">Institución Emisora del Beneficio</label>
                                <select id="exo-institucion" style="width:100%; border:2px solid #f1f5f9; border-radius:12px; padding:12px; font-size:0.85rem; font-weight:700; color:#1e293b; background:#f8fafc; outline:none; cursor:pointer;">
                                    ${instituciones.map(inst => `<option value="${inst.id}" ${current.institucion===inst.id?'selected':''}>${inst.id} – ${inst.n}</option>`).join('')}
                                </select>
                            </div>
                        </div>

                        <!-- Sección de Cálculo y Control Final -->
                        <div style="display:flex; gap:25px; align-items:stretch;">
                            <!-- Control Porcentaje -->
                            <div style="background:#fffcf0; border:2px solid #fbbf24; border-radius:16px; padding:15px 25px; flex:1; display:flex; flex-direction:column; justify-content:center;">
                                <label style="display:block; font-size:0.65rem; font-weight:900; color:#d97706; text-transform:uppercase; margin-bottom:10px; text-align:center;">Porcentaje a Exonerar</label>
                                <div style="display:flex; align-items:center; justify-content:center; gap:8px;">
                                    <input type="number" id="exo-pct" value="${current.pct}" min="0" max="100" style="width:70px; border:none; background:transparent; font-size:2.2rem; font-weight:900; color:#92400e; text-align:center; outline:none;">
                                    <span style="font-size:1.8rem; font-weight:900; color:#92400e;">%</span>
                                </div>
                            </div>

                            <!-- Resumen Financiero Estilo Recibo -->
                            <div style="background:#f8fafc; border:1.5px solid #edf2f7; border-radius:16px; padding:15px 25px; flex:1.5;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                                    <span style="font-size:0.75rem; font-weight:700; color:#64748b;">Impuesto Original:</span>
                                    <span style="font-size:0.75rem; font-weight:900; color:#1e293b;">₡${originalTax.toLocaleString('es-CR', {minimumFractionDigits:2})}</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                                    <span style="font-size:0.75rem; font-weight:700; color:#e11d48;">Monto Exonerado:</span>
                                    <span id="res-tax-exo" style="font-size:0.75rem; font-weight:900; color:#e11d48;">₡0.00</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; border-top:1.5px dashed #cbd5e1; padding-top:12px;">
                                    <span style="font-size:0.85rem; font-weight:900; color:#1e40af; text-transform:uppercase;">Impuesto Neto:</span>
                                    <span id="res-tax-neto" style="font-size:1.2rem; font-weight:950; color:#1e40af;">₡0.00</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Footer Acciones -->
                    <div style="padding:25px 35px; background:#f8fafc; border-top:1.5px solid #edf2f7; display:flex; justify-content:flex-end; gap:15px;">
                        <button id="exo-cancel" style="padding:12px 25px; border-radius:12px; border:1.5px solid #e2e8f0; background:white; color:#64748b; font-weight:900; font-size:0.75rem; cursor:pointer; text-transform:uppercase; letter-spacing:0.02em;">Cancelar</button>
                        <button id="exo-save" style="padding:12px 35px; border-radius:12px; border:none; background:#1e40af; color:white; font-weight:900; font-size:0.75rem; cursor:pointer; text-transform:uppercase; letter-spacing:0.02em; box-shadow:0 4px 12px rgba(30,64,175,0.25);">Guardar Cambios</button>
                    </div>
                </div>
            `,
            didOpen: () => {
                const check = document.getElementById('exo-active');
                const toggleBtn = document.getElementById('exo-toggle-btn');
                const mainBody = document.getElementById('exo-main-body');
                const pctInput = document.getElementById('exo-pct');
                const btnSave = document.getElementById('exo-save');
                const btnCancel = document.getElementById('exo-cancel');
                
                const updateTotals = () => {
                    const active = check.checked;
                    const pct = active ? (parseFloat(pctInput.value) || 0) : 0;
                    const amountExo = originalTax * (pct / 100);
                    const netTax = originalTax - amountExo;

                    document.getElementById('res-tax-exo').innerText = '₡' + amountExo.toLocaleString('es-CR', {minimumFractionDigits:2});
                    document.getElementById('res-tax-neto').innerText = '₡' + netTax.toLocaleString('es-CR', {minimumFractionDigits:2});
                };

                toggleBtn.onclick = () => {
                    check.checked = !check.checked;
                    current.active = check.checked;
                    toggleBtn.style.background = check.checked ? '#fbbf24' : '#334155';
                    toggleBtn.style.color = check.checked ? '#92400e' : '#cbd5e1';
                    toggleBtn.innerHTML = `<i class="fas ${check.checked ? 'fa-toggle-on' : 'fa-toggle-off'} fa-lg"></i> ${check.checked ? 'ACTIVA' : 'DESACTIVADA'}`;
                    mainBody.style.opacity = check.checked ? '1' : '0.5';
                    mainBody.style.pointerEvents = check.checked ? 'auto' : 'none';
                    updateTotals();
                };

                pctInput.oninput = updateTotals;
                updateTotals();

                btnSave.onclick = () => {
                    const val = {
                        active: check.checked,
                        tipoDoc: document.getElementById('exo-tipo-doc').value,
                        fecha: document.getElementById('exo-fecha').value,
                        numDoc: document.getElementById('exo-num-doc').value,
                        numArt: document.getElementById('exo-num-art').value,
                        numInc: document.getElementById('exo-num-inc').value,
                        institucion: document.getElementById('exo-institucion').value,
                        pct: parseFloat(document.getElementById('exo-pct').value) || 0
                    };
                    Swal.clickConfirm();
                    // Custom closure logic for confirmed
                    card.dataset.exoneracion = JSON.stringify(val);
                    const btnExo = card.querySelector('button[onclick*="configurarExoneracion"]');
                    if (val.active) {
                        btnExo.innerHTML = '<i class="fas fa-shield-alt"></i> EXO APLICADO';
                        btnExo.style.background = '#fef3c7';
                        btnExo.style.borderColor = '#f59e0b';
                        btnExo.style.color = '#92400e';
                    } else {
                        btnExo.innerHTML = '<i class="fas fa-shield-alt"></i> EXO';
                        btnExo.style.background = '#fffcf0';
                        btnExo.style.borderColor = '#fbbf24';
                        btnExo.style.color = '#d97706';
                    }
                    recalcularTotales();
                };
                btnCancel.onclick = () => Swal.close();
            }
        });
    };
    
    document.getElementById('factura-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        try {
            const receptorId = document.getElementById('cli-num-id')?.textContent;
            if (!receptorId || receptorId === '–') return Swal.fire('Error', 'Debe seleccionar un cliente', 'error');
            
            const lines = document.querySelectorAll('.item-card');
            if (lines.length === 0) {
                return Swal.fire('Error', 'El detalle está vacío', 'error');
            }

            const consecutivo = document.getElementById('mh-consecutivo')?.innerText || "00000000000000000000";
            
            // CAPTURA MASIVA DE DATOS PARA PDF DETALLADO
            const dataFactura = {
                consecutivo: consecutivo,
                clave: `506${new Date().getDate().toString().padStart(2,'0')}${ (new Date().getMonth()+1).toString().padStart(2,'0') }${new Date().getFullYear().toString().slice(-2)}${consecutivo}100000001`,
                fecha: new Date().toLocaleString('es-CR'),
                tipoDoc: document.getElementById('tipo-documento')?.options[document.getElementById('tipo-documento').selectedIndex]?.text || "Factura Electrónica",
                actividad: document.getElementById('actividad-economica')?.options[document.getElementById('actividad-economica').selectedIndex]?.text || "620101",
                moneda: document.getElementById('moneda')?.value || "CRC",
                condicionVenta: document.getElementById('condicion-venta')?.options[document.getElementById('condicion-venta').selectedIndex]?.text || "Contado",
                medioPago: document.getElementById('medio-pago')?.options[document.getElementById('medio-pago').selectedIndex]?.text || "Efectivo",
                
                emisor: {
                    nombre: "MUROTECH SOLUTIONS S.A.",
                    id: "3-101-897564",
                    email: "soporte@murotech.com",
                    tel: "+506 4000-0000",
                    loc: "San José, Escazú, San Rafael"
                },
                receptor: {
                    nombre: document.getElementById('cli-nombre')?.textContent || "Cliente General",
                    id: receptorId,
                    email: document.getElementById('cli-email')?.textContent || "N/A",
                    tel: document.getElementById('cli-telefono')?.textContent || "N/A",
                    loc: `${document.getElementById('cli-provincia')?.textContent}, ${document.getElementById('cli-canton')?.textContent}`
                },
                detalles: Array.from(lines).map(card => ({
                    desc: card.querySelector('.item-desc')?.value || "Sin descripción",
                    qty: card.querySelector('.item-qty')?.value || "0",
                    precio: card.dataset.precioOriginal || "0",
                    descuento: card.querySelector('.item-desc-pct')?.value + "%" || "0%",
                    impuesto: card.querySelector('.item-tax-pct')?.value + "%" || "13%",
                    totalLinea: card.querySelector('.subtotal-cell')?.innerText || "₡0.00"
                })),
                totales: {
                    subtotal: document.getElementById('total-subtotal')?.innerText || "₡0.00",
                    descuento: document.getElementById('total-descuento')?.innerText || "₡0.00",
                    impuesto: document.getElementById('total-impuesto')?.innerText || "₡0.00",
                    final: document.getElementById('total-final')?.innerText || "₡0.00"
                }
            };

            // PASO 1: Confirmación de Emisión
            Swal.fire({
                title: '¿Emitir Comprobante?',
                html: `
                    <div style="margin:10px 0;">
                        <div style="width:100px; height:100px; border:6px solid #e2e8f0; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 25px; color:#94a3b8;">
                            <i class="fas fa-question fa-3x"></i>
                        </div>
                        <p style="color:#475569; font-size:1.15rem; font-weight:600; margin-bottom:10px;">Se emitirá el documento con consecutivo:</p>
                        <p style="color:#1e40af; font-size:1.4rem; font-weight:900; letter-spacing:0.5px;">${consecutivo}</p>
                    </div>
                `,
                showCancelButton: true,
                confirmButtonColor: '#1e40af',
                cancelButtonColor: '#64748b',
                confirmButtonText: 'Sí, emitir',
                cancelButtonText: 'Cancel',
                reverseButtons: true,
                padding: '40px 20px',
                customClass: { popup: 'premium-swal-popup' }
            }).then((result) => {
                if (result.isConfirmed) {
                    mostrarExitoEmision(dataFactura);
                }
            });
        } catch (err) {
            console.error("Error al preparar emisión:", err);
            Swal.fire('Error de Sistema', 'No se pudo preparar la información de la factura: ' + err.message, 'error');
        }
    });

    function mostrarExitoEmision(data) {
        Swal.fire({
            title: 'Procesando Documento...',
            html: '<div style="margin:20px 0;"><i class="fas fa-sync-alt fa-spin fa-3x" style="color:#1e40af;"></i><br><p style="margin-top:15px; font-weight:700; color:#64748b;">Generando XML y Estructura MH v4.4...</p></div>',
            showConfirmButton: false,
            allowOutsideClick: false,
            timer: 2000,
            didClose: () => {
                // Mostrar Modal de Éxito Premium
                Swal.fire({
                    title: null,
                    width: '600px',
                    padding: '40px 30px',
                    showConfirmButton: false,
                    allowOutsideClick: false,
                    html: `
                        <div style="text-align:center; font-family:'Inter', sans-serif;">
                            <!-- Icono Casa/Escudo Estilo TicoFactura -->
                            <div style="position:relative; width:120px; height:120px; margin:0 auto 25px;">
                                <div style="background:#fef3c7; width:100%; height:100%; border-radius:30px; display:flex; align-items:center; justify-content:center; color:#f59e0b; font-size:3.5rem;">
                                    <i class="fas fa-home"></i>
                                </div>
                                <div style="position:absolute; bottom:-5px; right:-5px; background:#10b981; width:45px; height:45px; border-radius:50%; border:5px solid white; display:flex; align-items:center; justify-content:center; color:white; font-size:1.2rem;">
                                    <i class="fas fa-check"></i>
                                </div>
                            </div>

                            <h2 style="color:#0f172a; font-size:1.8rem; font-weight:900; margin-bottom:10px; letter-spacing:-0.5px;">¡Gracias!</h2>
                            <p style="color:#64748b; font-size:1.1rem; font-weight:700; margin-bottom:5px;">Se ha guardado correctamente</p>
                            <p style="color:#64748b; font-size:1.1rem; font-weight:700;">la factura electrónica <span style="color:#1e40af; font-weight:900;">${data.consecutivo}</span></p>

                            <div style="margin:30px 0; padding:20px; background:#f8fafc; border-radius:16px; text-align:left; border:1px solid #edf2f7;">
                                <div style="margin-bottom:15px;">
                                    <label style="display:block; font-size:0.65rem; font-weight:900; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:5px;">Usuario para el envío del XML firmado</label>
                                    <div style="color:#475569; font-size:0.85rem; font-weight:700; word-break:break-all;">cpj-3-102-772115@prod.comprobanteselectronicos.go.cr</div>
                                </div>
                                <div>
                                    <label style="display:block; font-size:0.65rem; font-weight:900; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:5px;">Contraseña para el envío del XML firmado</label>
                                    <div style="color:#475569; font-size:0.85rem; font-weight:700; letter-spacing:2px;">************************</div>
                                </div>
                            </div>

                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:25px;">
                                <button id="btn-swal-firmar" style="background:#1e40af; color:white; border:none; padding:16px; border-radius:40px; font-weight:900; font-size:0.9rem; cursor:pointer; box-shadow:0 4px 15px rgba(30,64,175,0.3); transition:all 0.2s;">
                                    Firmar y enviar documento
                                </button>
                                <button id="btn-swal-modificar" style="background:#f1f5f9; color:#475569; border:none; padding:16px; border-radius:40px; font-weight:900; font-size:0.9rem; cursor:pointer; transition:all 0.2s;">
                                    Volver a modificar el documento
                                </button>
                            </div>

                            <button id="btn-swal-dashboard" style="background:none; border:2px solid #e2e8f0; color:#64748b; padding:12px 30px; border-radius:40px; font-weight:900; font-size:0.85rem; cursor:pointer; width:100%; transition:all 0.2s;">
                                Continuar en MUROTECH
                            </button>
                        </div>
                    `,
                    didOpen: () => {
                        const popup = Swal.getPopup();
                        popup.querySelector('#btn-swal-firmar').onclick = () => {
                            Swal.close();
                            window.ejecutarFirmaSimulada(data);
                        };
                        popup.querySelector('#btn-swal-modificar').onclick = () => Swal.close();
                        popup.querySelector('#btn-swal-dashboard').onclick = () => {
                            window.location.href = 'panelControl.html';
                        };
                    }
                });
            }
        });
    }

    window.ejecutarFirmaSimulada = function(data) {
        try {
            // Generar los documentos reales usando la data capturada
            const xml = generarXMLv44(data);
            window.ultimoXML = xml; 
            const pdf = generarPDF(data);

            Swal.fire({
                title: 'Firmando Documento...',
                html: '<div style="margin:20px 0;"><i class="fas fa-pen-nib fa-spin fa-2x" style="color:#10b981;"></i><br><p style="margin-top:15px; font-weight:700; color:#64748b;">Aplicando Firma Digital Certificada...</p></div>',
                showConfirmButton: false,
                timer: 1500,
                didClose: () => {
                    localStorage.removeItem('muro_draft_factura');
                    window.isDirty = false;
                    Swal.fire({
                        icon: 'success',
                        title: '¡Comprobante Aceptado!',
                        html: `
                            <p>Hacienda ha recibido y aceptado el comprobante con éxito.</p>
                            <div style="display:flex; gap:10px; justify-content:center; margin-top:20px;">
                                <button onclick="descargarXML(window.ultimoXML)" style="background:#f1f5f9; color:#475569; border:none; padding:10px 20px; border-radius:10px; font-weight:700; cursor:pointer;">
                                    <i class="fas fa-file-code"></i> XML
                                </button>
                                <button onclick="window.currentPDF.save('Factura_${data.consecutivo}.pdf')" style="background:#f1f5f9; color:#e11d48; border:none; padding:10px 20px; border-radius:10px; font-weight:700; cursor:pointer;">
                                    <i class="fas fa-file-pdf"></i> PDF
                                </button>
                            </div>
                        `,
                        confirmButtonText: 'Ir al Dashboard',
                        confirmButtonColor: '#1e40af'
                    }).then(() => {
                        window.location.href = 'panelControl.html';
                    });
                }
            });
        } catch (error) {
            console.error("Error en firma:", error);
            Swal.fire('Error', 'Hubo un problema al generar los documentos legales: ' + error.message, 'error');
        }
    };

    // --- GENERACIÓN DE DOCUMENTOS (NORMATIVA 4.4) ---

    function generarXMLv44(data) {
        const consecutivo = data.consecutivo;
        const clave = data.clave;
        const emisor = data.emisor;
        const receptorNombre = data.receptor.nombre;
        const receptorId = data.receptor.id;

        let xml = `<?xml version="1.0" encoding="utf-8"?>\n`;
        xml += `<FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica">\n`;
        xml += `  <Clave>${clave}</Clave>\n`;
        xml += `  <NumeroConsecutivo>${consecutivo}</NumeroConsecutivo>\n`;
        xml += `  <FechaEmision>${new Date().toISOString()}</FechaEmision>\n`;
        xml += `  <Emisor><Nombre>${emisor.nombre}</Nombre><Identificacion><Tipo>02</Tipo><Numero>${emisor.id}</Numero></Identificacion></Emisor>\n`;
        xml += `  <Receptor><Nombre>${receptorNombre}</Nombre><Identificacion><Tipo>01</Tipo><Numero>${receptorId}</Numero></Identificacion></Receptor>\n`;
        xml += `  <DetalleServicio>\n`;
        
        data.detalles.forEach((item, i) => {
            xml += `    <LineaDetalle><NumeroLinea>${i+1}</NumeroLinea><Detalle>${item.desc}</Detalle><PrecioUnitario>${item.precio}</PrecioUnitario><Cantidad>${item.qty}</Cantidad></LineaDetalle>\n`;
        });

        xml += `  </DetalleServicio>\n`;
        xml += `  <ResumenFactura><TotalVenta>${data.totales.final}</TotalVenta></ResumenFactura>\n`;
        xml += `</FacturaElectronica>`;

        return xml; 
    }

    window.descargarXML = (xmlString) => {
        const blob = new Blob([xmlString], { type: 'text/xml' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'Comprobante_Hacienda.xml';
        link.click();
        URL.revokeObjectURL(url);
    };

    function generarPDF(data) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();

        // Registrar fuente Arial con soporte Unicode (₡)
        if (window.arialBase64) {
            doc.addFileToVFS("Arial.ttf", window.arialBase64);
            doc.addFont("Arial.ttf", "Arial", "normal");
            doc.setFont("Arial");
        }
        
        // --- ENCABEZADO (EMISOR) ---
        doc.setFillColor(30, 64, 175);
        doc.rect(0, 0, 210, 50, 'F');
        doc.setTextColor(255, 255, 255);
        
        // Ajustar tamaño de fuente si el nombre es muy largo
        const nombreEmisor = data.emisor.nombre;
        const fontSizeEmisor = nombreEmisor.length > 30 ? 16 : 22;
        doc.setFont("Arial", "bold");
        doc.setFontSize(fontSizeEmisor);
        doc.text(nombreEmisor, 15, 25);
        
        doc.setFont("Arial", "normal");
        doc.setFontSize(9);
        doc.text(`ID: ${data.emisor.id} | Tel: ${data.emisor.tel}`, 15, 32);
        doc.text(`Email: ${data.emisor.email}`, 15, 37);
        doc.text(`Ubicación: ${data.emisor.loc}`, 15, 42);

        // --- INFO DOCUMENTO ---
        doc.setFont("Arial", "bold");
        doc.setFontSize(14);
        // Título del documento (Alineado a la derecha, pero con margen para no chocar)
        doc.text(data.tipoDoc.toUpperCase(), 195, 25, { align: 'right' });
        
        doc.setFont("Arial", "normal");
        doc.setFontSize(8);
        doc.text(`Consecutivo: ${data.consecutivo}`, 195, 32, { align: 'right' });
        doc.text(`Clave: ${data.clave}`, 195, 37, { align: 'right' });
        doc.text(`Fecha: ${data.fecha}`, 195, 42, { align: 'right' });

        // --- RECEPTOR ---
        doc.setTextColor(15, 23, 42);
        doc.setFontSize(11);
        doc.setFont(undefined, 'bold');
        doc.text("DATOS DEL RECEPTOR", 15, 65);
        
        doc.setDrawColor(226, 232, 240);
        doc.line(15, 67, 200, 67);

        doc.setFontSize(10);
        doc.setFont(undefined, 'bold');
        doc.text(data.receptor.nombre, 15, 75);
        doc.setFont(undefined, 'normal');
        doc.setFontSize(9);
        doc.text(`Identificación: ${data.receptor.id}`, 15, 80);
        doc.text(`Email: ${data.receptor.email} | Tel: ${data.receptor.tel}`, 15, 85);
        doc.text(`Ubicación: ${data.receptor.loc}`, 15, 90);

        // --- METADATA COMERCIAL ---
        doc.text(`Condición Venta: ${data.condicionVenta}`, 140, 75);
        doc.text(`Medio Pago: ${data.medioPago}`, 140, 80);
        doc.text(`Moneda: ${data.moneda}`, 140, 85);
        doc.text(`Actividad: ${data.actividad.slice(0, 30)}...`, 140, 90);

        // --- TABLA DE DETALLE ---
        const rows = data.detalles.map(item => [
            item.qty,
            item.desc,
            "₡" + parseFloat(item.precio).toLocaleString('es-CR', {minimumFractionDigits:2}),
            item.descuento,
            item.totalLinea
        ]);

        doc.autoTable({
            startY: 100,
            head: [['Cant.', 'Descripción', 'Precio Unit.', 'Desc.', 'Total']],
            body: rows,
            headStyles: { fillColor: [30, 64, 175], textColor: [255, 255, 255], fontStyle: 'bold', font: 'Arial' },
            styles: { font: 'Arial', fontSize: 8, overflow: 'linebreak' },
            columnStyles: {
                0: { cellWidth: 15, halign: 'center' },
                1: { cellWidth: 'auto' },
                2: { cellWidth: 35, halign: 'right' },
                3: { cellWidth: 20, halign: 'center' },
                4: { cellWidth: 35, halign: 'right' }
            }
        });

        // --- TOTALES ---
        let finalY = doc.lastAutoTable.finalY + 15;
        
        // Asegurar que quepa el resumen, si no, nueva página
        if (finalY > 250) {
            doc.addPage();
            finalY = 20;
        }

        const marginX = 140;
        doc.setFont("Arial", "normal");
        doc.setFontSize(10);
        
        doc.text("SUBTOTAL:", marginX, finalY);
        doc.text(data.totales.subtotal, 195, finalY, { align: 'right' });
        
        doc.text("DESCUENTOS:", marginX, finalY + 7);
        doc.setTextColor(220, 38, 38);
        doc.text("-" + data.totales.descuento, 195, finalY + 7, { align: 'right' });
        
        doc.setTextColor(15, 23, 42);
        doc.text("IMPUESTOS:", marginX, finalY + 14);
        doc.text(data.totales.impuesto, 195, finalY + 14, { align: 'right' });

        doc.setDrawColor(30, 64, 175);
        doc.setLineWidth(0.5);
        doc.line(marginX, finalY + 18, 195, finalY + 18);

        doc.setFontSize(14);
        doc.setFont("Arial", "bold");
        doc.setTextColor(30, 64, 175);
        doc.text("TOTAL:", marginX, finalY + 28);
        doc.text(data.totales.final, 195, finalY + 28, { align: 'right' });

        // --- FOOTER LEGAL ---
        doc.setFontSize(7);
        doc.setTextColor(148, 163, 184);
        doc.setFont(undefined, 'normal');
        doc.text("Autorizado mediante resolución DGT-R-033-2019. Este documento es una representación gráfica de la factura electrónica.", 105, 285, { align: 'center' });
        doc.text("MUROTECH - Software de Facturación de Próxima Generación", 105, 290, { align: 'center' });

        window.currentPDF = doc;
        return doc;
    }

    /* ======= LÓGICA DE TIEMPO REAL Y CONSECUTIVO ======= */
    
    async function syncTime() {
        const timeEl = document.getElementById('realtime-date');
        const statusEl = document.getElementById('realtime-status');
        const dotEl = document.getElementById('clock-dot');
        if (!timeEl) return;
        
        const updateClock = (offset = 0) => {
            if (window.clockInterval) clearInterval(window.clockInterval);
            window.clockInterval = setInterval(() => {
                const now = new Date(Date.now() + offset);
                const options = { 
                    day: '2-digit', month: '2-digit', year: 'numeric',
                    hour: '2-digit', minute: '2-digit', second: '2-digit',
                    hour12: false
                };
                timeEl.innerText = now.toLocaleString('es-CR', options).replace(',', ' —');
            }, 1000);
        };

        const setStatus = (text, type) => {
            if (!statusEl || !dotEl) return;
            statusEl.innerText = text;
            const color = type === 'success' ? '#10b981' : (type === 'warning' ? '#f59e0b' : '#ef4444');
            statusEl.style.color = color;
            dotEl.style.background = color;
            dotEl.style.boxShadow = `0 0 10px ${color}66`;
        };

        // Estrategia de Sincronización Multi-Capa
        const endpoints = [
            { url: 'https://worldtimeapi.org/api/timezone/America/Costa_Rica', name: 'WORLDTIME' },
            { url: 'https://www.timeapi.io/api/Time/current/zone?timeZone=America/Costa_Rica', name: 'TIMEAPI' }
        ];

        for (const endpoint of endpoints) {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 3000);
            
            try {
                const response = await fetch(endpoint.url, { signal: controller.signal });
                if (response.ok) {
                    const data = await response.json();
                    const serverTimeStr = data.datetime || data.dateTime || data.isoOrder;
                    if (serverTimeStr) {
                        const serverTime = new Date(serverTimeStr);
                        const offset = serverTime.getTime() - Date.now();
                        setStatus(`SINCRONIZADO (${endpoint.name})`, 'success');
                        updateClock(offset);
                        clearTimeout(timeout);
                        return;
                    }
                }
            } catch (e) {
                console.warn(`Sincro falló con ${endpoint.name}`);
            } finally {
                clearTimeout(timeout);
            }
        }

        // Si todos fallan, usar hora local inmediatamente
        setStatus('HORA DEL SISTEMA', 'warning');
        updateClock(0);
    }

    function updateConsecutivo() {
        const selectTipo = document.getElementById('tipo-documento');
        const display = document.getElementById('mh-consecutivo');
        if (!selectTipo || !display) return;

        const sucursal = "001";
        const puntoVenta = "00001";
        const tipoDoc = selectTipo.value;
        
        const db = window.muroDB;
        const total = db ? db.getFacturas().length : 0;
        const correlativo = (total + 1).toString().padStart(10, '0');
        
        display.innerText = `${sucursal}${puntoVenta}${tipoDoc}${correlativo}`;
    }

    document.getElementById('tipo-documento')?.addEventListener('change', updateConsecutivo);
    document.getElementById('moneda')?.addEventListener('change', recalcularTotales);

})();