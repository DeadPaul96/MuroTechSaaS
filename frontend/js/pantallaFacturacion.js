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

        // --- LÓGICA DE PRODUCTOS ---
        (function() {
            const input = document.getElementById('buscar-cabys');
            const dropdown = document.getElementById('cabys-dropdown');

            function closeDropdown() { dropdown.style.display = 'none'; }

            input.addEventListener('input', function() {
                const q = this.value.trim().toLowerCase();
                if (q.length < 1) { closeDropdown(); return; }
                const db = window.muroDB;
                if (!db) return;
                
                // Optimización: Nombre, Detalle, Descripción y Código CABYS
                const matches = db.getProductos().filter(p => 
                    multiWordMatch(`${p.nombre || ''} ${p.detalle || ''} ${p.descripcion || ''} ${p.cabys || ''} ${p.codigo || ''}`, q)
                ).slice(0, 10);

                dropdown.innerHTML = '';
                if (!matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">Sin resultados</div>';
                } else {
                    matches.forEach(prod => {
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.innerHTML = `
                            <div style="flex:1;">
                                <div style="font-weight:800; color:#1e293b;">${prod.nombre || prod.descripcion}</div>
                                <div style="font-size:0.75rem; color:#64748b;">CABYS: ${prod.cabys || '—'} | Cód: ${prod.codigo || '—'}</div>
                            </div>
                            <div style="font-weight:900; color:#1e40af;">${monedaSymbols[document.getElementById('moneda').value]}${(prod.precioVenta || prod.precio || 0).toFixed(2)}</div>
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

            tr.innerHTML = `
                <td style="color:#94a3b8; font-weight:800; font-size:0.75rem;">#${lineCount}</td>
                <td><input type="text" class="fi-grid cabys-code" value="${prod.cabys || ''}" readonly></td>
                <td><input type="text" class="fi-grid item-code" value="${prod.codigo || prod.sku || ''}" readonly></td>
                <td><input type="text" class="fi-grid item-desc" value="${prod.nombre || prod.descripcion}" readonly></td>
                <td><input type="text" class="fi-grid item-detail" value="${prod.detalle || ''}" placeholder="Marca, modelo..."></td>
                <td>
                    <select class="fi-grid item-tax-type" onchange="recalcularTotales()">
                        <option value="01">IVA</option>
                        <option value="02">ISC</option>
                        <option value="99">Otro</option>
                    </select>
                </td>
                <td><input type="number" class="fi-grid item-tax-pct" value="13" min="0" max="100" step="0.1" oninput="recalcularTotales()"></td>
                <td><input type="number" class="fi-grid item-qty" value="1" min="1" step="0.001" oninput="recalcularTotales()"></td>
                <td><input type="number" class="fi-grid item-desc-pct" value="0" min="0" max="100" step="0.1" oninput="validateDiscount(this); recalcularTotales();"></td>
                <td style="font-weight:900; color:#1e40af; text-align:right; padding-right:15px;" class="subtotal-cell">${symbol}0.00</td>
                <td><button type="button" class="btn-del" onclick="eliminarLinea('${tr.id}')"><i class="fas fa-trash-alt"></i></button></td>
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

                    const base = cant * prec;
                    const descMonto = Math.round((base * (descPct / 100)) * 100) / 100;
                    const subtotalNeto = base - descMonto;
                    const taxMonto = Math.round((subtotalNeto * (taxPct / 100)) * 100) / 100;
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
                const res = await fetch("https://api.hacienda.go.cr/indicadores/tc");
                if (res.ok) {
                    const data = await res.json();
                    currentRates.usd = data.dolar?.venta?.valor || 530;
                    document.getElementById('fx-usd-venta').textContent = '₡' + currentRates.usd.toFixed(2);
                    document.getElementById('dash-tc-status').innerHTML = '<i class="fas fa-check-circle"></i> SINCRONIZADO';
                }
            } catch (e) { console.warn("TC falló."); }
        }

        // --- EMITIR ---
        document.getElementById('factura-form').onsubmit = (e) => {
            e.preventDefault();
            const lineas = document.querySelectorAll('#detalle-lineas tr:not(#empty-row)');
            if (!lineas.length) return Swal.fire('Error', 'Debe agregar ítems.', 'error');
            
            Swal.fire({
                title: 'Emitiendo...',
                text: 'Procesando con Hacienda Costa Rica',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            setTimeout(() => {
                localStorage.removeItem('murotech_factura_draft');
                Swal.fire('¡Éxito!', 'Comprobante emitido correctamente.', 'success').then(() => window.location.reload());
            }, 2000);
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