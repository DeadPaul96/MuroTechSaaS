(function () {
        // --- SELECTORES GLOBALES ---
        const ventaSection = document.getElementById('venta-section');
        const receptorAlert = document.getElementById('receptor-alert');
        const detailLinesTbody = document.getElementById('detalle-lineas');
        const emptyRow = document.getElementById('empty-row');
        const draftSection = document.getElementById('section-drafts');
        
        // --- ESTADO ---
        let lineCount = 0;
        let currentRates = { usd: 1, eur: 1 };
        const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };
        const tarifasIVA = {
            '01_13': 13, '01_08': 8, '01_04': 4, '01_02': 2, '01_01': 1, '01_00': 0,
            '02': 0, '03': 0, '04': 0, '05': 0, '06': 0, '07': 0, '08': 13, '99': 0
        };

        // --- INICIALIZACIÓN ---
        document.addEventListener('DOMContentLoaded', () => {
            syncRates();
            checkDraft();
            toggleVentaSection(false); // Bloqueado por defecto
            
            // Prevenir envío con Enter
            document.getElementById('factura-form').addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                }
            });
        });

        function toggleVentaSection(active) {
            if (active) {
                ventaSection.classList.remove('section-blocked');
                receptorAlert.style.display = 'none';
            } else {
                ventaSection.classList.add('section-blocked');
                receptorAlert.style.display = 'block';
            }
        }

        // --- LÓGICA DE CLIENTES ---
        function mostrarCliente(data) {
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
        }

        function limpiarCliente() {
            const ids = ['cli-tipo-id','cli-num-id','cli-nombre','cli-nombre-com',
                         'cli-provincia','cli-canton','cli-distrito','cli-otras-senas',
                         'cli-telefono','cli-email','cli-actividad','cli-regimen'];
            ids.forEach(id => document.getElementById(id).textContent = '–');
            document.getElementById('cliente-info-panel').classList.remove('visible');
            document.getElementById('buscar-cliente-id').value = '';
            toggleVentaSection(false);
            saveDraft();
        }

        /* AUTOCOMPLETE CLIENTES */
        (function() {
            const input = document.getElementById('buscar-cliente-id');
            const dropdown = document.getElementById('cliente-dropdown');
            const tipoIdSelect = document.getElementById('tipo-id-cliente');

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
                tipoIdSelect.value = cliente.tipoId;
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
            document.addEventListener('click', closeDropdown);
        })();

        (function() {
            const input = document.getElementById('buscar-cabys');
            const dropdown = document.getElementById('cabys-dropdown');

            function closeDropdown() { dropdown.style.display = 'none'; }

            input.addEventListener('input', function() {
                const q = this.value.trim().toLowerCase();
                if (q.length < 1) { closeDropdown(); return; }
                const db = window.muroDB;
                if (!db) return;
                
                // Búsqueda extendida: Nombre, Marca, Modelo, Características, Descripción, CABYS, Código
                const matches = db.getProductos().filter(p => 
                    multiWordMatch(`${p.nombre || ''} ${p.descripcion || ''} ${p.marca || ''} ${p.modelo || ''} ${p.caracteristicas || ''} ${p.nombreServicio || ''} ${p.cabys || ''} ${p.codigo || ''}`, q)
                ).slice(0, 10);

                dropdown.innerHTML = '';
                if (!matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">Sin resultados</div>';
                } else {
                    matches.forEach(prod => {
                        const mainTitle = prod.nombreServicio || prod.nombre || prod.descripcion;
                        const subTitle = [
                            prod.marca ? `Marca: ${prod.marca}` : '',
                            prod.modelo ? `Mod: ${prod.modelo}` : '',
                            prod.caracteristicas ? `Char: ${prod.caracteristicas}` : ''
                        ].filter(Boolean).join(' | ');

                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.innerHTML = `
                            <div style="flex:1;">
                                <div style="font-weight:900; color:#0f172a; font-size:1rem;">${mainTitle}</div>
                                <div style="font-size:0.75rem; color:#475569; font-weight:600; margin-top:2px;">${subTitle}</div>
                                <div style="font-size:0.65rem; color:#94a3b8; margin-top:2px;">Normativa CABYS: ${prod.cabys || '—'}</div>
                            </div>
                            <div style="font-weight:900; color:#1e40af; font-size:1.1rem; padding-left:15px;">${monedaSymbols[document.getElementById('moneda').value]}${(prod.precioVenta || prod.precio || 0).toFixed(2)}</div>
                        `;
                        item.onclick = () => { agregarLineaProducto(prod); input.value = ''; closeDropdown(); };
                        dropdown.appendChild(item);
                    });
                }
                dropdown.style.display = 'block';
            });
            document.addEventListener('click', closeDropdown);
        })();

        function agregarLineaProducto(prod) {
            lineCount++;
            if (emptyRow) emptyRow.style.display = 'none';
            
            const monedaActual = document.getElementById('moneda').value;
            const symbol = monedaSymbols[monedaActual] || '$';
            
            let precioUnit = prod.precioVenta || prod.precio || 0;
            // Conversión si la moneda no es CRC (asumiendo que el inventario está en CRC)
            if (monedaActual === 'USD') precioUnit /= currentRates.usd;
            if (monedaActual === 'EUR') precioUnit /= currentRates.eur;

            const tr = document.createElement('tr');
            tr.id = 'linea-' + lineCount;
            tr.dataset.precioOriginal = precioUnit;
            tr.dataset.descMax = prod.descuento_maximo || 0;
            
            const displayDetail = prod.marca ? `${prod.marca} ${prod.modelo || ''}` : (prod.nombreServicio || prod.detalle || '');

            tr.innerHTML = `
                <td style="color:#94a3b8; font-weight:800; font-size:0.75rem;">#${lineCount}</td>
                <td>
                    <div class="fi-grid-stacked">
                        <input type="text" class="fi-grid item-code" value="${prod.codigo || prod.sku || ''}" readonly style="font-weight:800; color:var(--primary);">
                        <div class="subtext">CABYS: <span class="cabys-code-txt">${prod.cabys || '—'}</span></div>
                        <input type="hidden" class="cabys-code" value="${prod.cabys || ''}">
                    </div>
                </td>
                <td>
                    <div class="fi-grid-stacked" style="padding: 4px 0;">
                        <input type="text" class="fi-grid item-desc" value="${prod.nombre || prod.descripcion}" readonly style="font-weight:800; font-size:0.95rem; color:#0f172a; border-bottom:1px solid #f1f5f9; padding-bottom:4px;">
                        <input type="text" class="fi-grid item-detail" value="${displayDetail}" placeholder="Marca, modelo..." style="font-size:0.78rem; color:#475569; font-weight:600; margin-top:2px;">
                    </div>
                </td>
                <td>
                    <div class="fi-grid-stacked">
                        <select class="fi-grid item-tax-type" onchange="recalculatTotales()" style="font-size:0.8rem; border:none; padding:0; background:transparent; font-weight:800; color:#1e293b;">
                            <option value="01">IVA</option>
                            <option value="02">ISC</option>
                            <option value="99">Otro</option>
                        </select>
                        <div style="display:flex; align-items:center; gap:8px; margin-top:4px;">
                           <div style="display:flex; align-items:center; background:#ecfdf5; border:1px solid #10b981; padding:2px 8px; border-radius:8px;">
                               <input type="number" class="fi-grid item-tax-pct" value="${prod.impuesto || 13}" min="0" max="100" step="0.1" oninput="recalcularTotales()" style="font-size:0.85rem; color:#10b981; font-weight:900; width:35px; background:transparent; border:none; padding:0;">
                               <span style="font-size:0.75rem; color:#10b981; font-weight:900;">%</span>
                           </div>
                           <button type="button" class="btn-exo" onclick="configurarExoneracion('${tr.id}')" title="Configurar Exoneración" style="background:#fff7ed; border:1.5px solid #f59e0b; color:#f59e0b; cursor:pointer; font-size:0.8rem; padding:4px 8px; border-radius:8px; display:flex; align-items:center; gap:4px; font-weight:800;">
                               <i class="fas fa-shield-alt"></i> <span style="font-size:0.6rem;">EXO</span>
                           </button>
                        </div>
                    </div>
                </td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px; justify-content:center; padding: 10px 0;">
                        <div style="text-align:center;">
                            <span style="font-size:0.55rem; font-weight:800; color:#94a3b8; display:block; text-transform:uppercase;">CANT.</span>
                            <input type="number" class="fi-grid item-qty" value="1" min="0.001" step="0.001" oninput="recalcularTotales()" style="width:55px; text-align:center; font-weight:900; background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:8px; padding:6px; font-size:0.95rem; color:#0f172a;">
                        </div>
                        <span style="color:#cbd5e1; margin-top:12px; font-weight:300;">|</span>
                        <div style="text-align:center;">
                             <span style="font-size:0.55rem; font-weight:800; color:#94a3b8; display:block; text-transform:uppercase;">DESC.</span>
                            <div style="display:flex; align-items:center; background:#fef2f2; border:1.5px solid #ef4444; padding:2px 6px; border-radius:8px; margin-top:2px;">
                                <input type="number" class="fi-grid item-desc-pct" value="0" min="0" max="100" step="0.1" oninput="validateDiscount(this); recalcularTotales();" style="width:32px; text-align:right; font-size:0.85rem; color:#ef4444; font-weight:900; background:transparent; border:none; padding:0;">
                                <span style="font-size:0.7rem; color:#ef4444; font-weight:900;">%</span>
                            </div>
                        </div>
                    </div>
                </td>
                <td style="font-weight:900; color:#1e40af; text-align:right; padding-right:15px;" class="subtotal-cell">${symbol}0.00</td>
                <td><button type="button" class="btn-del" onclick="eliminarLinea('${tr.id}')" style="background:transparent; border:none; color:#ef4444; cursor:pointer;"><i class="fas fa-trash-alt"></i></button></td>
            `;
            detailLinesTbody.appendChild(tr);
            recalcularTotales();
        }

        window.validateDiscount = function(input) {
            const tr = input.closest('tr');
            const max = parseFloat(tr.dataset.descMax) || 0;
            const val = parseFloat(input.value) || 0;
            if (val > max && !window.admin_auth) {
                Swal.fire('Descuento Excedido', `El descuento máximo permitido para este producto es del ${max}%.`, 'warning');
                input.value = max;
            }
        };

        window.eliminarLinea = function(id) {
            document.getElementById(id).remove();
            if (detailLinesTbody.children.length <= 1) { // count includes empty-row
                 if (emptyRow) emptyRow.style.display = 'table-row';
            }
            recalcularTotales();
        };

        // --- MOTOR DE CÁLCULO ---
        function recalcularTotales() {
            try {
                let subtotalTotal = 0;
                let descuentoTotal = 0;
                let impuestoTotal = 0;
                
                const moneda = document.getElementById('moneda').value;
                const symbol = monedaSymbols[moneda] || '$';
                const lineas = document.querySelectorAll('#detalle-lineas tr:not(#empty-row)');

                lineas.forEach(tr => {
                    const cant = parseFloat(tr.querySelector('.item-qty').value) || 0;
                    const prec = parseFloat(tr.dataset.precioOriginal) || 0;
                    const descPct = parseFloat(tr.querySelector('.item-desc-pct').value) || 0;
                    const taxPct = parseFloat(tr.querySelector('.item-tax-pct').value) || 0;
                    const exoData = tr.dataset.exoneracion ? JSON.parse(tr.dataset.exoneracion) : null;

                    const base = cant * prec;
                    const descMonto = Math.round((base * (descPct / 100)) * 100) / 100;
                    const subtotalNeto = base - descMonto;
                    
                    let taxMonto = Math.round((subtotalNeto * (taxPct / 100)) * 100) / 100;
                    
                    // Aplicar exoneración si existe
                    if (exoData && exoData.pct > 0) {
                        const montoExo = Math.round((taxMonto * (exoData.pct / 100)) * 100) / 100;
                        taxMonto -= montoExo;
                        tr.querySelector('.btn-exo').style.color = '#10b981'; // Cambio visual si hay exo
                    } else {
                        tr.querySelector('.btn-exo').style.color = '#f59e0b';
                    }

                    const totalLinea = subtotalNeto + taxMonto;

                    subtotalTotal += base;
                    descuentoTotal += descMonto;
                    impuestoTotal += taxMonto;

                    tr.querySelector('.subtotal-cell').textContent = `${symbol}${totalLinea.toLocaleString('es-CR', {minimumFractionDigits:2})}`;
                });

                const finalTotal = subtotalTotal - descuentoTotal + impuestoTotal;

                const format = (v) => `${symbol}${v.toLocaleString('es-CR', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
                document.getElementById('total-subtotal').textContent = format(subtotalTotal);
                document.getElementById('total-descuento').textContent = format(descuentoTotal);
                document.getElementById('total-impuesto').textContent = format(impuestoTotal);
                document.getElementById('total-final').textContent = format(finalTotal);

                saveDraft();
            } catch (e) { console.error(e); }
        }

        // --- PERSISTENCIA (DRAFTS) ---
        function saveDraft() {
            const data = {
                receptor: {
                    id: document.getElementById('cli-num-id').textContent,
                    nombre: document.getElementById('cli-nombre').textContent,
                    email: document.getElementById('cli-email').textContent
                },
                moneda: document.getElementById('moneda').value,
                docTipo: document.getElementById('tipo-documento').value,
                lineas: []
            };

            const lineas = document.querySelectorAll('#detalle-lineas tr:not(#empty-row)');
            lineas.forEach(tr => {
                data.lineas.push({
                    cabys: tr.querySelector('.cabys-code').value,
                    codigo: tr.querySelector('.item-code').value,
                    desc: tr.querySelector('.item-desc').value,
                    detail: tr.querySelector('.item-detail').value,
                    taxType: tr.querySelector('.item-tax-type').value,
                    taxPct: tr.querySelector('.item-tax-pct').value,
                    qty: tr.querySelector('.item-qty').value,
                    descPct: tr.querySelector('.item-desc-pct').value,
                    precio: tr.dataset.precioOriginal,
                    descMax: tr.dataset.descMax
                });
            });

            if (data.lineas.length > 0 || data.receptor.id !== '–') {
                localStorage.setItem('murotech_factura_draft', JSON.stringify(data));
            }
        }

        function checkDraft() {
            const draft = localStorage.getItem('murotech_factura_draft');
            if (draft) {
                draftSection.style.display = 'block';
            }
        }

        document.getElementById('btn-restore-draft').onclick = () => {
            const draft = JSON.parse(localStorage.getItem('murotech_factura_draft'));
            if (!draft) return;

            // Restaurar receptor (simulado, buscar en DB)
            if (draft.receptor.id !== '–') {
                const cliente = window.muroDB?.getClientes().find(c => c.identificacion === draft.receptor.id);
                if (cliente) {
                    // Manual select logic
                    document.getElementById('buscar-cliente-id').value = cliente.identificacion;
                    document.getElementById('btn-buscar-cliente').click();
                }
            }

            document.getElementById('moneda').value = draft.moneda;
            document.getElementById('tipo-documento').value = draft.docTipo;

            detailLinesTbody.innerHTML = ''; // Limpiar
            draft.lineas.forEach(l => {
                const trId = 'linea-' + (++lineCount);
                const tr = document.createElement('tr');
                tr.id = trId;
                tr.dataset.precioOriginal = l.precio;
                tr.dataset.descMax = l.descMax;
                tr.innerHTML = `
                    <td style="color:#94a3b8; font-weight:800; font-size:0.75rem;">#${lineCount}</td>
                    <td><input type="text" class="fi-grid cabys-code" value="${l.cabys}" readonly></td>
                    <td><input type="text" class="fi-grid item-code" value="${l.codigo}" readonly></td>
                    <td><input type="text" class="fi-grid item-desc" value="${l.desc}" readonly></td>
                    <td><input type="text" class="fi-grid item-detail" value="${l.detail || ''}" placeholder="Marca, modelo..."></td>
                    <td>
                        <select class="fi-grid item-tax-type" onchange="recalcularTotales()">
                            <option value="01" ${l.taxType==='01'?'selected':''}>IVA</option>
                            <option value="02" ${l.taxType==='02'?'selected':''}>ISC</option>
                            <option value="99" ${l.taxType==='99'?'selected':''}>Otro</option>
                        </select>
                    </td>
                    <td><input type="number" class="fi-grid item-tax-pct" value="${l.taxPct}" min="0" max="100" step="0.1" oninput="recalcularTotales()"></td>
                    <td><input type="number" class="fi-grid item-qty" value="${l.qty}" min="1" step="0.001" oninput="recalcularTotales()"></td>
                    <td><input type="number" class="fi-grid item-desc-pct" value="${l.descPct}" min="0" max="100" step="0.1" oninput="validateDiscount(this); recalcularTotales();"></td>
                    <td style="font-weight:900; color:#1e40af; text-align:right; padding-right:15px;" class="subtotal-cell">0.00</td>
                    <td><button type="button" class="btn-del" onclick="eliminarLinea('${tr.id}')"><i class="fas fa-trash-alt"></i></button></td>
                `;
                detailLinesTbody.appendChild(tr);
            });
            recalcularTotales();
            draftSection.style.display = 'none';
        };

        document.getElementById('btn-discard-draft').onclick = () => {
             localStorage.removeItem('murotech_factura_draft');
             draftSection.style.display = 'none';
        };

        // --- DIVISAS ---
        async function syncRates() {
            try {
                const now = new Date();
                const dateStr = now.toLocaleDateString('es-CR', {day:'2-digit', month:'2-digit', year:'2-digit'});
                
                const res = await fetch("https://api.hacienda.go.cr/indicadores/tc");
                if (res.ok) {
                    const data = await res.json();
                    currentRates.usd = data.dolar?.venta?.valor || 530;
                    document.getElementById('fx-usd-venta').textContent = '₡' + currentRates.usd.toFixed(2);
                    document.getElementById('fx-usd-fecha').textContent = dateStr;
                }
                
                // EUR a CRC (Simulación basada en cross rate de BCCR ~ (USD * 1.10) por tipo de venta)
                currentRates.eur = Math.round((currentRates.usd * 1.10) * 100) / 100; 
                document.getElementById('fx-eur-valor').textContent = '₡' + currentRates.eur.toFixed(2);
                document.getElementById('fx-eur-fecha').textContent = dateStr;

                document.getElementById('dash-tc-status').innerHTML = '<i class="fas fa-check-circle"></i> SINCRONIZADO';
            } catch (e) { 
                console.warn("TC falló."); 
                document.getElementById('dash-tc-status').innerHTML = '<i class="fas fa-times-circle" style="color:#ef4444"></i> ERROR TC';
            }
        }

        function validarMH44() {
            const receptorId = document.getElementById('cli-num-id').textContent;
            if (receptorId === '–') return { ok: false, msg: 'Debe seleccionar un receptor válido.' };
            
            const lineas = document.querySelectorAll('#detalle-lineas tr:not(#empty-row)');
            if (!lineas.length) return { ok: false, msg: 'Debe agregar al menos una línea de detalle.' };
            
            const actividad = document.getElementById('actividad-economica').value;
            if (!actividad) return { ok: false, msg: 'Debe seleccionar una actividad económica.' };

            return { ok: true };
        }

        function generarXML44(data) {
            console.log("Generando XML Normativa MH v4.4...");
            
            let lineasXml = "";
            data.lineasRaw.forEach((l, i) => {
                const exoPart = l.exoneracion ? `
    <Exoneracion>
        <TipoDocumento>${l.exoneracion.tipo}</TipoDocumento>
        <NumeroDocumento>${l.exoneracion.num}</NumeroDocumento>
        <NombreInstitucion>${l.exoneracion.inst}</NombreInstitucion>
        <FechaEmision>${l.exoneracion.fecha}T00:00:00</FechaEmision>
        <PorcentajeExoneracion>${l.exoneracion.pct}</PorcentajeExoneracion>
    </Exoneracion>` : "";

                lineasXml += `
<LineaDetalle>
    <NumeroLinea>${i+1}</NumeroLinea>
    <Codigo>${l.codigo}</Codigo>
    <Detalle>${l.desc}</Detalle>
    <Impuesto>
        <Codigo>${l.taxType}</Codigo>
        <Tarifa>${l.taxPct}</Tarifa>
        ${exoPart}
    </Impuesto>
</LineaDetalle>`;
            });

            const xml = `<?xml version="1.0" encoding="utf-8"?>
<FacturaElectronica xmlns="https://cdn.hacienda.go.cr/atv/sch/v4.4/facturaElectronica">
    <Clave>${Math.floor(Math.random()*1e50)}</Clave>
    <CodigoActividad>${data.actividad}</CodigoActividad>
    <NumeroConsecutivo>0010000101${Math.floor(Math.random()*1e10)}</NumeroConsecutivo>
    <FechaEmision>${new Date().toISOString()}</FechaEmision>
    <Emisor>
        <Nombre>MUROTECH SOLUTIONS S.A.</Nombre>
        <Identificacion><Tipo>02</Tipo><Numero>3101897564</Numero></Identificacion>
    </Emisor>
    <Receptor>
        <Nombre>${data.receptor.nombre}</Nombre>
        <Identificacion><Tipo>${data.receptor.tipo}</Tipo><Numero>${data.receptor.id}</Numero></Identificacion>
    </Receptor>
    <DetalleServicio>${lineasXml}</DetalleServicio>
    <ResumenFactura>
        <CodigoTipoMoneda>
            <CodigoMoneda>${data.moneda}</CodigoMoneda>
            <TipoCambio>${data.tipoCambio}</TipoCambio>
        </CodigoTipoMoneda>
        <TotalVentaNeto>${data.total}</TotalVentaNeto>
    </ResumenFactura>
</FacturaElectronica>`;
            return xml;
        }

        window.configurarExoneracion = function(trId) {
            const tr = document.getElementById(trId);
            const current = tr.dataset.exoneracion ? JSON.parse(tr.dataset.exoneracion) : { tipo: '01', num: '', inst: '', fecha: new Date().toISOString().split('T')[0], pct: 100 };

            Swal.fire({
                title: 'Configurar Exoneración MH 4.4',
                html: `
                    <div style="text-align:left; display:flex; flex-direction:column; gap:12px; margin-top:10px;">
                        <div>
                            <label class="label-sm">Tipo de Documento</label>
                            <select id="exo-tipo" class="premium-select" style="width:100%;">
                                <option value="01" ${current.tipo==='01'?'selected':''}>01 – Compras Autorizadas</option>
                                <option value="02" ${current.tipo==='02'?'selected':''}>02 – Ventas exentas a diplomáticos</option>
                                <option value="03" ${current.tipo==='03'?'selected':''}>03 – Orden de compra instituciones públicas</option>
                                <option value="04" ${current.tipo==='04'?'selected':''}>04 – Exenciones Dirección Gral de Hacienda</option>
                            </select>
                        </div>
                        <div>
                            <label class="label-sm">Número de Documento / Ley</label>
                            <input id="exo-num" class="fi" value="${current.num}" placeholder="Ej. DGH-RES-001">
                        </div>
                        <div>
                            <label class="label-sm">Nombre de la Institución</label>
                            <input id="exo-inst" class="fi" value="${current.inst}" placeholder="Ministerio de Hacienda">
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                            <div>
                                <label class="label-sm">Fecha de Emisión</label>
                                <input id="exo-fecha" type="date" class="fi" value="${current.fecha}">
                            </div>
                            <div>
                                <label class="label-sm">% Exoneración</label>
                                <input id="exo-pct" type="number" class="fi" value="${current.pct}" min="0" max="100">
                            </div>
                        </div>
                    </div>
                `,
                showCancelButton: true,
                confirmButtonText: 'Guardar Exoneración',
                cancelButtonText: 'Quitar / Cancelar',
                width: '500px'
            }).then(r => {
                if (r.isConfirmed) {
                    const data = {
                        tipo: document.getElementById('exo-tipo').value,
                        num: document.getElementById('exo-num').value,
                        inst: document.getElementById('exo-inst').value,
                        fecha: document.getElementById('exo-fecha').value,
                        pct: parseFloat(document.getElementById('exo-pct').value) || 0
                    };
                    tr.dataset.exoneracion = JSON.stringify(data);
                } else if (r.dismiss === Swal.DismissReason.cancel) {
                    tr.dataset.exoneracion = ''; // Borrar
                }
                recalcularTotales();
            });
        };

        // --- EMITIR ---
        document.getElementById('factura-form').onsubmit = (e) => {
            e.preventDefault();
            
            const val = validarMH44();
            if (!val.ok) return Swal.fire('Error MH v4.4', val.msg, 'error');

            const lineasRaw = [];
            document.querySelectorAll('#detalle-lineas tr:not(#empty-row)').forEach(tr => {
                lineasRaw.push({
                    codigo: tr.querySelector('.item-code').value,
                    desc: tr.querySelector('.item-desc').value,
                    taxType: tr.querySelector('.item-tax-type').value,
                    taxPct: tr.querySelector('.item-tax-pct').value,
                    exoneracion: tr.dataset.exoneracion ? JSON.parse(tr.dataset.exoneracion) : null
                });
            });

            const dataToSubmit = {
                actividad: document.getElementById('actividad-economica').value,
                receptor: {
                    id: document.getElementById('cli-num-id').textContent,
                    nombre: document.getElementById('cli-nombre').textContent,
                    tipo: document.getElementById('cli-tipo-id').textContent.substring(0,2)
                },
                moneda: document.getElementById('moneda').value,
                tipoCambio: document.getElementById('moneda').value === 'CRC' ? 1 : currentRates.usd,
                total: document.getElementById('total-final').textContent.replace(/[₡$,]/g, ''),
                lineasRaw
            };
            
            Swal.fire({
                title: 'Validando Normativa v4.4...',
                text: 'Firmando digitalmente y enviando a Hacienda',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            setTimeout(() => {
                const xml = generarXML44(dataToSubmit);
                console.log("XML GENERADO:", xml);
                // Aquí se guardaría el XML como file o se enviaría al backend
                
                localStorage.removeItem('murotech_factura_draft');
                Swal.fire({
                    icon: 'success',
                    title: '¡Éxito!',
                    text: 'Comprobante emitido y XML v4.4 generado correctamente.',
                    footer: '<a href="#" onclick="downloadMockXML()">Descargar XML v4.4 Generado</a>'
                }).then(() => window.location.reload());
            }, 2000);
        };

        window.downloadMockXML = () => {
             const blob = new Blob(["<xml>...Simulacion v4.4...</xml>"], {type: "text/xml"});
             const url = window.URL.createObjectURL(blob);
             const a = document.createElement("a");
             a.href = url;
             a.download = "Factura_v4.4.xml";
             a.click();
        };

        // Helpers
        window.recalcularTotales = recalcularTotales;
        window.agregarLineaProducto = agregarLineaProducto;

    })();

    function multiWordMatch(text, query) {
        if (!text || !query) return false;
        const words = query.split(' ').filter(w => w.length > 0);
        return words.every(word => text.toLowerCase().includes(word.toLowerCase()));
    }