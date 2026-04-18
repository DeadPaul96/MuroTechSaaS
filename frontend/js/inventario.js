(function () {
        const cabysData = window.CABYS_DATA || [];
        const searchInput = document.getElementById('inv-buscar-cabys');
        const resultsDiv  = document.getElementById('cabys-results');
        const cabysInput  = document.getElementById('inv-cabys-numero');
        const nombreInput = document.getElementById('inv-nombre');
        const ivaSelect   = document.getElementById('inv-iva');
        const statusTxt   = document.getElementById('cabys-status-txt');
        const statusEl    = document.getElementById('cabys-status');

        if (cabysData.length) {
            statusEl.style.color = '#10b981';
            statusTxt.textContent = `Catálogo CAByS listo — ${cabysData.length.toLocaleString()} ítems`;
        }


        searchInput.addEventListener('input', function () {
            const q = this.value.trim().toLowerCase();
            resultsDiv.innerHTML = '';
            if (q.length < 2) { 
                resultsDiv.style.display = 'none'; 
                return; 
            }

            const matches = cabysData.filter(m => multiWordMatch(`${m.d} ${m.c}`, q)).slice(0, 30);
            if (!matches.length) { 
                resultsDiv.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron resultados</div>';
                resultsDiv.style.display = 'block';
                return; 
            }

            matches.forEach(m => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';
                div.innerHTML = `
                    <div class="autocomplete-info">
                        <div class="autocomplete-name">${m.d}</div>
                        <div class="autocomplete-subinfo">
                            <span class="autocomplete-badge">${m.c}</span>
                            <span>IVA Sugerido: ${m.i}%</span>
                        </div>
                    </div>
                    <div class="autocomplete-tax">${m.i}% IVA</div>
                `;
                div.addEventListener('click', () => {
                    // ── Auto-completar TODOS los campos posibles ──
                    cabysInput.value = m.c;
                    nombreInput.value = m.d;
                    searchInput.value = m.d;
                    ivaSelect.value = String(m.i);
                    const tipoImp = document.getElementById('inv-tipo-impuesto');
                    if (tipoImp) tipoImp.value = '01';

                    // Unidad de medida inteligente
                    const desc = m.d.toLowerCase();
                    const unidadSel = document.getElementById('inv-unidad-medida');
                    if (/servicio|consultor|asesor|mantenimiento|reparaci|instalaci|limpieza|capacitaci|transporte|diseño|desarrollo|auditor/i.test(desc)) {
                        unidadSel.value = 'Svc';
                    } else if (/kg|kilogram/i.test(desc)) {
                        unidadSel.value = 'Kg';
                    } else if (/litro|galon/i.test(desc)) {
                        unidadSel.value = 'L';
                    } else if (/metro|m²|m2/i.test(desc)) {
                        unidadSel.value = 'm';
                    } else if (/gramo/i.test(desc)) {
                        unidadSel.value = 'g';
                    } else if (/mililitro|ml/i.test(desc)) {
                        unidadSel.value = 'ml';
                    } else {
                        unidadSel.value = 'Unid';
                    }

                    const prefix = m.d.replace(/[^A-Za-z]/g, '').substring(0, 3).toUpperCase();
                    const suffix = m.c.slice(-4);
                    document.getElementById('inv-codigo-interno').value = `${prefix}-${suffix}`;

                    resultsDiv.style.display = 'none';
                    toggleCtxPanels();

                    ['inv-cabys-numero','inv-nombre','inv-iva','inv-unidad-medida','inv-tipo-impuesto','inv-codigo-interno'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) {
                            el.style.transition = 'box-shadow 0.3s';
                            el.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.25)';
                            setTimeout(() => el.style.boxShadow = '', 1500);
                        }
                    });
                });
                resultsDiv.appendChild(div);
            });
            resultsDiv.style.display = 'block';
        });

        // Cerrar al click afuera
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
                resultsDiv.style.display = 'none';
            }
        });


        function calcularPrecioVenta() {
            const costo = parseFloat(document.getElementById('inv-precio-linea').value) || 0;
            const ganancia = parseFloat(document.getElementById('inv-ganancia').value) || 0;
            if (costo > 0) {
                document.getElementById('inv-precio').value = (costo * (1 + ganancia / 100)).toFixed(2);
            }
        }
        document.getElementById('inv-precio-linea').addEventListener('input', calcularPrecioVenta);
        document.getElementById('inv-ganancia').addEventListener('input', calcularPrecioVenta);

        /* ── Paneles contextuales Producto / Servicio ──────────── */
        const ctxProducto = document.getElementById('ctx-producto');
        const ctxServicio = document.getElementById('ctx-servicio');
        const stockRow = document.getElementById('stock-row');
        const btnSubmitTxt = document.getElementById('btn-submit-txt');
        const unidadMedidaSel = document.getElementById('inv-unidad-medida');

        function toggleCtxPanels() {
            const esServicio = unidadMedidaSel.value === 'Svc';
            
            ctxProducto.classList.toggle('active', !esServicio);
            ctxServicio.classList.toggle('active', esServicio);

            // Servicios no tienen stock
            if (esServicio) {
                stockRow.style.display = 'none';
                btnSubmitTxt.textContent = 'REGISTRAR SERVICIO';
            } else {
                stockRow.style.display = '';
                btnSubmitTxt.textContent = 'REGISTRAR PRODUCTO';
            }
        }

        unidadMedidaSel.addEventListener('change', toggleCtxPanels);
        // Inicial: mostrar panel producto por defecto
        toggleCtxPanels();

        let inventario = window.muroDB ? window.muroDB.getProductos() : [];

        function renderTabla() {
            const tbody = document.getElementById('lista-inventario');
            tbody.innerHTML = '';
            inventario.forEach(item => {
                const esServicio = item.unidadMedida === 'Svc';
                const tipo = esServicio ? 'Svc' : 'Prod';
                const tipoBadge = esServicio
                    ? '<span style="font-size:0.65rem;background:#f3e8ff;color:#7c3aed;padding:2px 6px;border-radius:4px;font-weight:700;">SERVICIO</span>'
                    : '<span style="font-size:0.65rem;background:#dcfce7;color:#15803d;padding:2px 6px;border-radius:4px;font-weight:700;">PRODUCTO</span>';

                let detalle = '';
                if (esServicio) {
                    const parts = [];
                    if (item.nombreServicio) parts.push(`<strong>${item.nombreServicio}</strong>`);
                    if (item.detalleServicio) parts.push(item.detalleServicio);
                    if (parts.length) detalle = `<div style="font-size:0.72rem;color:#7c3aed;margin-top:2px;">${parts.join(' — ')}</div>`;
                } else if (item.marca || item.modelo || item.caracteristicas) {
                    const parts = [];
                    if (item.marca) parts.push(item.marca);
                    if (item.modelo) parts.push(item.modelo);
                    if (item.caracteristicas) parts.push(item.caracteristicas);
                    detalle = `<div style="font-size:0.72rem;color:#64748b;margin-top:2px;">${parts.join(' · ')}</div>`;
                }

                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid #f1f5f9';
                tr.style.transition = 'all 0.2s';
                tr.onmouseover = () => tr.style.background = '#f8fafc';
                tr.onmouseout = () => tr.style.background = '';
                tr.innerHTML = `
                    <td style="padding:15px 20px;">
                        <div style="font-family:monospace; font-size:0.7rem; color:#64748b;">${item.cabys}</div>
                        <div style="font-weight:800; color:var(--primary); font-size:0.8rem; margin-top:2px;">${item.codigo}</div>
                    </td>
                    <td style="padding:15px 20px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            ${tipoBadge}
                            <span style="font-weight:800; color:#1e293b; font-size:0.9rem;">${item.descripcion}</span>
                        </div>
                        ${detalle}
                    </td>
                    <td style="padding:15px 20px;">
                        <div style="font-size:0.75rem; color:#94a3b8; font-weight:600;">Costo: ₡${item.precio ? item.precio.toLocaleString() : '0'}</div>
                        <div style="font-weight:900; color:#1e293b; font-size:0.95rem; margin-top:2px;">Venta: ₡${item.precioVenta ? item.precioVenta.toLocaleString() : '0'}</div>
                    </td>
                    <td style="padding:15px 20px;">
                        <div style="display:inline-block; background:#f1f5f9; padding:2px 8px; border-radius:6px; font-weight:800; font-size:0.7rem; color:#64748b;">
                            ${item.impuesto}% IVA
                        </div>
                        <div style="font-size:0.65rem; color:#10b981; font-weight:800; margin-top:4px; padding-left:4px;">
                            UTIL: ${item.margen || 0}%
                        </div>
                    </td>
                    <td style="padding:15px 20px; text-align:center;">
                        <div style="font-weight:900; font-size:1.1rem; color:${item.stock > 0 ? '#10b981' : '#ef4444'}">
                            ${esServicio ? '<span style="color:#94a3b8; font-size:0.75rem; font-style:italic; font-weight:500;">ILIM</span>' : item.stock}
                        </div>
                        <div style="font-size:0.6rem; font-weight:800; color:#94a3b8; text-transform:uppercase;">${esServicio ? 'Servicio' : 'Stock'}</div>
                    </td>
                    <td style="padding:15px 20px; text-align:center; display:flex; justify-content:center; gap:8px; align-items:center;">
                        <button class="btn-action edit" onclick="editarItem(${item.id})" title="Editar Ítem" style="width:34px; height:34px; border-radius:10px; border:none; background:#eff6ff; color:#3b82f6; cursor:pointer; transition:all 0.2s;">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-action del" onclick="eliminarItem(${item.id})" title="Eliminar Ítem" style="width:34px; height:34px; border-radius:10px; border:none; background:#fef2f2; color:#ef4444; cursor:pointer; transition:all 0.2s;">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            document.getElementById('total-items-badge').innerHTML = `<i class="fas fa-box"></i> ${inventario.length} Ítems en Inventario`;
        }

        window.editarItem = function(id) {
            const item = inventario.find(i => i.id === id);
            if (!item) return;
            const esServicio = item.unidadMedida === 'Svc';

            Swal.fire({
                title: 'Editar Ítem del Inventario',
                html: `
                    <div style="display:flex; flex-direction:column; gap:12px; margin-top: 15px; text-align:left;">
                        <div>
                            <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Descripción General (MH)</label>
                            <input id="swal-desc" class="fi" value="${item.descripcion}" style="box-sizing:border-box; width:100%;">
                        </div>
                        
                        ${!esServicio ? `
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Marca</label>
                                <input id="swal-marca" class="fi" value="${item.marca || ''}" style="box-sizing:border-box; width:100%;">
                            </div>
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Modelo</label>
                                <input id="swal-modelo" class="fi" value="${item.modelo || ''}" style="box-sizing:border-box; width:100%;">
                            </div>
                        </div>
                        ` : `
                        <div>
                            <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Nombre del Servicio</label>
                            <input id="swal-nombre-svc" class="fi" value="${item.nombreServicio || ''}" style="box-sizing:border-box; width:100%;">
                        </div>
                        `}

                        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Costo Base</label>
                                <input id="swal-costo" type="number" class="fi" value="${item.precio || 0}" style="box-sizing:border-box; width:100%;">
                            </div>
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Ganancia (%)</label>
                                <input id="swal-margen" type="number" class="fi" value="${item.margen || 0}" style="box-sizing:border-box; width:100%;">
                            </div>
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Monto Venta</label>
                                <input id="swal-venta" type="number" class="fi" value="${item.precioVenta || 0}" style="box-sizing:border-box; width:100%; font-weight:800; background:#f8fafc; color:var(--primary);">
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Descuento Máximo (%)</label>
                                <input id="swal-desc-max" type="number" class="fi" value="${item.descuento_maximo || 0}" style="box-sizing:border-box; width:100%;">
                            </div>
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Stock Actual</label>
                                <input id="swal-stock" type="number" class="fi" value="${item.stock}" ${esServicio ? 'disabled' : ''} style="box-sizing:border-box; width:100%;">
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Tipo de Impuesto (Normativa 4.4)</label>
                                <select id="swal-tipo-impuesto" class="premium-select" disabled style="width:100%; background:#f1f5f9; pointer-events:none; opacity:0.8;">
                                    <option value="01" ${item.tipoImpuesto == '01' ? 'selected' : ''}>01 – IVA (Valor Agregado)</option>
                                    <option value="02" ${item.tipoImpuesto == '02' ? 'selected' : ''}>02 – ISC (Consumo)</option>
                                    <option value="03" ${item.tipoImpuesto == '03' ? 'selected' : ''}>03 – Imp. Único Combustibles</option>
                                    <option value="04" ${item.tipoImpuesto == '04' ? 'selected' : ''}>04 – Imp. Ley 6946 (alcohol)</option>
                                    <option value="99" ${item.tipoImpuesto == '99' ? 'selected' : ''}>99 – Otros</option>
                                </select>
                            </div>
                            <div>
                                <label style="font-size:0.7rem; font-weight:800; color:#64748b; margin-left:12px; display:block; margin-bottom:4px;">Tarifa de Impuesto (%) [Asignado por CABYS]</label>
                                <select id="swal-iva" class="premium-select" disabled style="width:100%; background:#f1f5f9; pointer-events:none; opacity:0.8;">
                                    <option value="13" ${item.impuesto == '13' ? 'selected' : ''}>13% (General)</option>
                                    <option value="8" ${item.impuesto == '8' ? 'selected' : ''}>8% (Reducida)</option>
                                    <option value="4" ${item.impuesto == '4' ? 'selected' : ''}>4% (Reducida)</option>
                                    <option value="2" ${item.impuesto == '2' ? 'selected' : ''}>2% (Reducida)</option>
                                    <option value="1" ${item.impuesto == '1' ? 'selected' : ''}>1% (Especial)</option>
                                    <option value="0" ${item.impuesto == '0' ? 'selected' : ''}>0% (Exento)</option>
                                </select>
                            </div>
                        </div>
                    </div>
                `,
                didOpen: () => {
                    const inCosto = document.getElementById('swal-costo');
                    const inMargen = document.getElementById('swal-margen');
                    const inVenta = document.getElementById('swal-venta');

                    const recalcular = () => {
                        const c = parseFloat(inCosto.value) || 0;
                        const m = parseFloat(inMargen.value) || 0;
                        if (c > 0) {
                            inVenta.value = (c * (1 + m / 100)).toFixed(2);
                        }
                    };

                    inCosto.oninput = recalcular;
                    inMargen.oninput = recalcular;
                },
                showCancelButton: true,
                confirmButtonText: 'Guardar Cambios',
                cancelButtonText: 'Cancelar',
                width: '650px'
            }).then(r => {
                if (r.isConfirmed) {
                    const updatedData = {
                        descripcion: document.getElementById('swal-desc').value,
                        precio: parseFloat(document.getElementById('swal-costo').value),
                        margen: parseFloat(document.getElementById('swal-margen').value),
                        precioVenta: parseFloat(document.getElementById('swal-venta').value),
                        descuento_maximo: parseFloat(document.getElementById('swal-desc-max').value) || 0,
                        stock: esServicio ? 0 : parseInt(document.getElementById('swal-stock').value),
                        impuesto: document.getElementById('swal-iva').value,
                        tipoImpuesto: document.getElementById('swal-tipo-impuesto').value
                    };

                    if (!esServicio) {
                        updatedData.marca = document.getElementById('swal-marca').value;
                        updatedData.modelo = document.getElementById('swal-modelo').value;
                    } else {
                        updatedData.nombreServicio = document.getElementById('swal-nombre-svc').value;
                    }
                    
                    if (window.muroDB) window.muroDB.updateProducto(id, updatedData);
                    inventario = window.muroDB.getProductos();
                    renderTabla();
                    Swal.fire('Catálogo Actualizado', 'Los valores de costo y utilidad han sido recalculados.', 'success');
                }
            });
        };

        window.eliminarItem = function(id) {
            Swal.fire({
                title: '¿Eliminar ítem?',
                text: 'Esta acción no se puede deshacer.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#ef4444',
                cancelButtonText: 'Cancelar',
                confirmButtonText: 'Sí, eliminar'
            }).then(r => {
                if (r.isConfirmed) {
                    if (window.muroDB) window.muroDB.deleteProducto(id);
                    inventario = window.muroDB.getProductos();
                    renderTabla();
                }
            });
        };

        document.getElementById('addItemForm').addEventListener('submit', function (e) {
            e.preventDefault();
            const esServicio = unidadMedidaSel.value === 'Svc';
            const producto = {
                id: Date.now(),
                cabys: cabysInput.value,
                codigo: document.getElementById('inv-codigo-interno').value || `SKU-${Date.now()}`,
                descripcion: nombreInput.value,
                unidadMedida: unidadMedidaSel.value,
                impuesto: ivaSelect.value,
                precioVenta: parseFloat(document.getElementById('inv-precio').value),
                stock: esServicio ? 0 : parseInt(document.getElementById('inv-stock').value),
                // Campos según tipo
                marca: esServicio ? '' : (document.getElementById('inv-marca').value || ''),
                modelo: esServicio ? '' : (document.getElementById('inv-modelo').value || ''),
                caracteristicas: esServicio ? '' : (document.getElementById('inv-caracteristicas').value || ''),
                nombreServicio: esServicio ? (document.getElementById('inv-nombre-servicio').value || '') : '',
                detalleServicio: esServicio ? (document.getElementById('inv-detalle-servicio').value || '') : '',
                descuento_maximo: parseFloat(document.getElementById('inv-descuento-max').value) || 0
            };
            if (window.muroDB) window.muroDB.addProducto(producto);
            inventario = window.muroDB.getProductos();
            renderTabla();
            this.reset();
            toggleCtxPanels();
            Swal.fire('Éxito', esServicio ? 'Servicio registrado' : 'Producto registrado', 'success');
        });

        /* ======= FILTRADO DE TABLA DE INVENTARIO ======= */
        document.getElementById('buscar-inventario').addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            const rows = document.querySelectorAll('#lista-inventario tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = multiWordMatch(text, q) ? '' : 'none';
            });
        });

        /* ======= IMPORTACIÓN MASIVA EXCEL ======= */
        document.getElementById('file-upload-inv').addEventListener('change', function(e) {
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
                    
                    const p = {
                        id: Date.now() + i,
                        cabys: row[0] || '0000000000000',
                        codigo: row[1] || `IMP-${Date.now()}-${i}`,
                        descripcion: row[2] || 'Producto Generico',
                        unidadMedida: row[3] || 'Unid',
                        impuesto: parseFloat(row[4]) || 13,
                        precioVenta: parseFloat(row[5]) || 0,
                        stock: parseInt(row[6]) || 0
                    };
                    if (window.muroDB) window.muroDB.addProducto(p);
                    count++;
                }
                inventario = window.muroDB.getProductos();
                renderTabla();
                Swal.fire('Catálogo Actualizado', `Se importaron ${count} ítems correctamente.`, 'success');
                document.getElementById('file-upload-inv').value = '';
            };
            reader.readAsArrayBuffer(file);
        });

        renderTabla();
    })();