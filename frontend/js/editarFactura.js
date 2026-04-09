// --- MOTOR DEL EDITOR PREMIUM MUROTECH v4.6 ---
        const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };
        let currentRates = { usd: 0, eur: 0 }; // Se actualiza con la API de Hacienda
        let editDoc = null;
        let lineCount = 0;

        document.addEventListener('DOMContentLoaded', () => {
            syncRates();        // Conectar a Hacienda inmediatamente
            loadInvoiceFromURL();
        });



        async function syncRates() {
            const urlDirecta = "https://api.hacienda.go.cr/indicadores/tc";
            const urlProxy = "proxy_hacienda.php";
            let data = null;

            try {
                // Intento 1: Proxy local
                const resProxy = await fetch(urlProxy);
                if (resProxy.ok) data = await resProxy.json();
            } catch (e) {
                console.warn("Proxy no disponible en Editor, intentando API directa...");
            }

            if (!data) {
                try {
                    // Intento 2: API Directa Hacienda
                    const resDirecta = await fetch(urlDirecta);
                    if (resDirecta.ok) data = await resDirecta.json();
                } catch (e) {
                    console.error("Fallo total de conexión Hacienda.");
                }
            }

            if (data) {
                if (data.dolar && data.dolar.venta) {
                    currentRates.usd = data.dolar.venta.valor;
                    document.getElementById('fx-usd-venta').textContent = '₡' + currentRates.usd.toFixed(2);
                    document.getElementById('fx-usd-fecha').textContent = data.dolar.venta.fecha.split('-').reverse().join('/');
                }
                if (data.euro) {
                    currentRates.eur = data.euro.colones;
                    document.getElementById('fx-eur-valor').textContent = '₡' + currentRates.eur.toFixed(2);
                    document.getElementById('fx-eur-fecha').textContent = data.euro.fecha.split('-').reverse().join('/');
                }
                document.getElementById('dash-tc-status').innerHTML = '<i class="fas fa-check-circle"></i> SINCRONIZADO';
                document.getElementById('dash-tc-status').style.background = '#ecfdf5';
                document.getElementById('dash-tc-status').style.color = '#10b981';
            } else {
                document.getElementById('dash-tc-status').innerHTML = '<i class="fas fa-exclamation-triangle"></i> ERROR API';
                document.getElementById('dash-tc-status').style.background = '#fef2f2';
                document.getElementById('dash-tc-status').style.color = '#ef4444';
            }
        }


        function loadInvoiceFromURL() {
            const params = new URLSearchParams(window.location.search);
            const docId = params.get('id');
            const badge = document.getElementById('doc-status-badge');
            
            if(!docId) {
                if(badge) badge.innerHTML = '<span class="status-badge" style="background:#f1f5f9; color:#64748b; border:1px solid #e2e8f0;"><i class="fas fa-search"></i> ESPERANDO SELECCIÓN</span>';
                // Pequeño delay para que el usuario vea la página antes del modal
                setTimeout(() => mostrarSelectorComprobantes(), 600);
                return;
            }
            const db = window.muroDB;
            if(!db) return;
            const all = db.getFacturas();
            editDoc = all.find(f => f.id === docId);
            if(editDoc) {
                poblarDatosCompleto(editDoc);
            } else {
                if(badge) badge.innerHTML = '<span class="status-badge" style="background:#fee2e2; color:#b91c1c; border-color:#fecaca;"><i class="fas fa-exclamation-triangle"></i> NO ENCONTRADO</span>';
            }
        }

        function poblarDatosCompleto(doc) {
            if(!doc) return;
            editDoc = doc;
            
            // Datos Básicos
            document.getElementById('document-id').value = doc.id;
            document.getElementById('fecha-emision').value = (doc.fecha || new Date().toISOString()).split('T')[0];
            document.getElementById('moneda').value = doc.moneda || 'CRC';
            document.getElementById('observaciones').value = doc.observaciones || '';
            document.getElementById('condicion-venta').value = doc.condicionVenta || '01';
            document.getElementById('medio-pago').value = doc.medioPago || '01';
            
            const badge = document.getElementById('doc-status-badge');
            const boxRef = document.getElementById('box-referencia');

            if(doc.estado === 'Borrador') {
                badge.innerHTML = '<span class="status-badge mode-draft"><i class="fas fa-edit"></i> BORRADOR ACTIVO</span>';
                boxRef.style.display = 'none';
                document.getElementById('btn-finalizar').innerHTML = '<i class="fas fa-save"></i> ACTUALIZAR Y EMITIR';
                document.getElementById('document-id').removeAttribute('readonly');
                document.getElementById('document-id').style.background = '#ffffff';
            } else {
                badge.innerHTML = '<span class="status-badge mode-credit"><i class="fas fa-redo"></i> MODO NOTA DE CRÉDITO</span>';
                boxRef.style.display = 'block';
                document.getElementById('ref-id').value = doc.id;
                document.getElementById('btn-finalizar').innerHTML = '<i class="fas fa-paper-plane"></i> GENERAR CORRECCIÓN';
                document.getElementById('document-id').setAttribute('readonly', true);
                document.getElementById('document-id').style.background = '#f1f5f9';
            }

            // Priorizar receptor incrustado en el documento (Paul Zuñiga etc.)
            const db = window.muroDB;
            let clienteParaUI = doc.receptor || null;
            
            if(!clienteParaUI && db) {
                clienteParaUI = db.getClientes().find(c => c.id == doc.clienteId || c.nombre == doc.clienteNombre);
            }
            
            // Si no hay nada, usar un placeholder o el nombre guardado en doc.clienteNombre
            if(!clienteParaUI) {
                clienteParaUI = {
                    nombre: doc.clienteNombre || 'Cliente Contado',
                    identificacion: 'N/A',
                    provincia: 'N/A',
                    canton: 'N/A',
                    correo: 'N/A'
                };
            }
            
            poblarClienteUI(clienteParaUI);

            // Cargar Líneas
            const tbody = document.getElementById('detalle-lineas');
            tbody.innerHTML = '';
            lineCount = 0;
            
            if(doc.detalle && doc.detalle.length) {
                doc.detalle.forEach(item => agregarLinea(item));
            } else {
                // Si no tiene líneas (doc antiguo), crear una basada en el monto total
                agregarLinea({ 
                    descripcion: 'Servicios Profesionales / Concepto Original', 
                    precio: doc.monto / 1.13, 
                    cantidad: 1,
                    cabys: '000000',
                    descuento: 0
                });
            }
            recalcularTotales();
        }

        function poblarClienteUI(c) {
            if(!c) return;
            const panel = document.getElementById('cliente-info-panel');
            panel.className = 'info-panel-editable';
            panel.innerHTML = `
                <div class="cliente-card-segment">
                    <div class="segment-header">
                        <i class="fas fa-user-circle"></i>
                        <h4>Identidad del Receptor</h4>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:12px;">
                        <div>
                            <label class="label-sm">Nombre / Razón Social</label>
                            <input type="text" class="edit-fi" value="${c.nombre}" id="edit-cli-nombre" style="font-weight:900; color:var(--primary-dark);">
                        </div>
                        <div>
                            <label class="label-sm">Cédula / Identificación</label>
                            <input type="text" class="edit-fi" value="${c.identificacion}" id="edit-cli-id">
                        </div>
                    </div>
                </div>
                <div class="cliente-card-segment">
                    <div class="segment-header">
                        <i class="fas fa-map-marker-alt"></i>
                        <h4>Ubicación y Contacto</h4>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div style="grid-column: span 2;">
                            <label class="label-sm">Correo Electrónico</label>
                            <input type="email" class="edit-fi" value="${c.correo || 'N/A'}" id="edit-cli-mail" style="color:var(--primary); font-weight:800;">
                        </div>
                        <div>
                            <label class="label-sm">Provincia</label>
                            <input type="text" class="edit-fi" value="${c.provincia || 'N/A'}" id="edit-cli-prov">
                        </div>
                        <div>
                            <label class="label-sm">Cantón</label>
                            <input type="text" class="edit-fi" value="${c.canton || 'N/A'}" id="edit-cli-cant">
                        </div>
                    </div>
                </div>
            `;
            panel.dataset.clienteId = c.id;
        }

        /* ======= MOTOR DE CLIENTES CON AUTOCOMPLETE PREMIUM ======= */
        (function() {
            const input = document.getElementById('buscar-cliente');
            const dropdown = document.getElementById('cliente-dropdown');

            function closeDropdown() {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
            }

            function renderResults(results) {
                dropdown.innerHTML = '';
                if (!results.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron clientes</div>';
                    dropdown.style.display = 'block';
                    return;
                }

                results.forEach(cliente => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `
                        <div class="autocomplete-info">
                            <div class="autocomplete-name">${cliente.nombre}</div>
                            <div class="autocomplete-subinfo">
                                <span class="autocomplete-badge">${cliente.identificacion}</span>
                                <span>${cliente.correo || ''}</span>
                            </div>
                        </div>
                    `;
                    item.onclick = (e) => {
                        e.stopPropagation();
                        poblarClienteUI(cliente);
                        input.value = cliente.identificacion;
                        closeDropdown();
                        Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Cliente vinculado', showConfirmButton: false, timer: 1500 });
                    };
                    dropdown.appendChild(item);
                });
                dropdown.style.display = 'block';
            }

            input.addEventListener('input', function() {
                const q = this.value.trim().toLowerCase();
                if (q.length < 1) {
                    closeDropdown();
                    return;
                }
                const db = window.muroDB;
                if (!db) return;
                const matches = db.getClientes().filter(c => 
                    multiWordMatch(`${c.nombre} ${c.identificacion} ${c.correo || ''}`, q)
                ).slice(0, 10);
                renderResults(matches);
            });

            window.buscarNuevoCliente = function() {
                const q = input.value.trim().toLowerCase();
                if (!q) return Swal.fire('Atención', 'Ingrese algo para buscar', 'warning');
                const db = window.muroDB;
                if (!db) return;
                const clientes = db.getClientes();
                let found = clientes.find(c => c.identificacion.replace(/[-\s]/g, '') === q.replace(/[-\s]/g, ''));
                if (!found) found = clientes.find(c => multiWordMatch(`${c.nombre} ${c.identificacion}`, q));
                if (found) {
                    poblarClienteUI(found);
                    input.value = found.identificacion;
                    closeDropdown();
                    Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Cliente vinculado', showConfirmButton: false, timer: 1500 });
                } else {
                    Swal.fire('No encontrado', 'No existe el cliente en la DB local.', 'error');
                }
            };

            input.addEventListener('click', (e) => e.stopPropagation());
            dropdown.addEventListener('click', (e) => e.stopPropagation());
            document.addEventListener('click', closeDropdown);
        })();

        window.agregarLineaManual = function() {
            agregarLinea();
        };

        function agregarLinea(data = null) {
            lineCount++;
            const tbody = document.getElementById('detalle-lineas');
            const empty = document.getElementById('empty-row');
            if(empty) empty.remove();

            const moneda = document.getElementById('moneda').value;
            const symbol = monedaSymbols[moneda] || '₡';
            const tr = document.createElement('tr');
            tr.id = 'line-' + lineCount;
            
            let cabys = data ? (data.cabys || '00000000') : '';
            let desc = data ? (data.descripcion || data.nombre || '') : '';
            let cant = data ? (data.cantidad || 1) : 1;
            let precio = data ? (data.precioVenta || data.precio || 0) : 0;
            let descVal = data ? (data.descuento || 0) : 0;

            // Conversión automática usando la tasa oficial de Hacienda (currentRates)
            if (data && (data.precioVenta || data.precio)) {
                if (moneda === 'USD') precio = precio / currentRates.usd;
                else if (moneda === 'EUR') precio = precio / currentRates.eur;
                // CRC: sin cambio
            }



            tr.innerHTML = `
                <td style="color:#94a3b8; font-weight:800; font-size:0.7rem;">#${lineCount}</td>
                <td><input type="text" class="fi cabys-i" value="${cabys}" style="padding:6px; font-size:0.75rem;"></td>
                <td><input type="text" class="fi desc-i" value="${desc}" style="padding:6px; font-size:0.75rem;"></td>
                <td><input type="number" class="fi cant-i text-center" value="${cant}" min="1" style="padding:6px;" oninput="recalcularTotales()"></td>
                <td><input type="number" class="fi precio-i" value="${precio.toFixed(2)}" step="0.01" style="padding:6px;" oninput="recalcularTotales()"></td>
                <td><input type="number" class="fi disc-i" value="${descVal.toFixed(2)}" step="0.01" style="padding:6px;" oninput="recalcularTotales()"></td>
                <td style="text-align:right; font-weight:800; color:var(--primary-dark);" class="line-subtotal">${symbol}0.00</td>
                <td><button type="button" onclick="eliminarLinea(${lineCount})" style="border:none; background:none; color:#ef4444; cursor:pointer;"><i class="fas fa-trash-alt"></i></button></td>
            `;
            tbody.appendChild(tr);
            recalcularTotales();
        }

        window.eliminarLinea = function(id) {
            const tr = document.getElementById('line-' + id);
            if(tr) tr.remove();
            if(!document.querySelectorAll('#detalle-lineas tr').length) {
                document.getElementById('detalle-lineas').innerHTML = '<tr id="empty-row"><td colspan="8" style="text-align:center; padding:30px; color:#94a3b8;">No hay líneas cargadas.</td></tr>';
            }
            recalcularTotales();
        }

        function recalcularTotales() {
            const moneda = document.getElementById('moneda').value;
            const symbol = monedaSymbols[moneda] || '₡';
            const tasaIVA = (parseFloat(document.getElementById('tipo-impuesto').value) || 0) / 100;

            let subtotalBruto = 0;
            let descuentosTotales = 0;

            document.querySelectorAll('#detalle-lineas tr:not(#empty-row)').forEach(tr => {
                const c = parseFloat(tr.querySelector('.cant-i').value) || 0;
                const p = parseFloat(tr.querySelector('.precio-i').value) || 0;
                const d = parseFloat(tr.querySelector('.disc-i').value) || 0;
                
                const brLinea = c * p;
                const netoLinea = Math.max(brLinea - d, 0);
                
                subtotalBruto += brLinea;
                descuentosTotales += d;
                
                tr.querySelector('.line-subtotal').textContent = symbol + netoLinea.toLocaleString('es-CR',{minimumFractionDigits:2});
            });

            const netoFinal = Math.max(subtotalBruto - descuentosTotales, 0);
            const iva = Math.round((netoFinal * tasaIVA) * 100) / 100;
            const total = netoFinal + iva;

            document.getElementById('total-subtotal').textContent = symbol + subtotalBruto.toLocaleString('es-CR',{minimumFractionDigits:2});
            document.getElementById('total-descuentos').textContent = symbol + descuentosTotales.toLocaleString('es-CR',{minimumFractionDigits:2});
            document.getElementById('total-impuesto').textContent = symbol + iva.toLocaleString('es-CR',{minimumFractionDigits:2});
            document.getElementById('total-final').textContent = symbol + total.toLocaleString('es-CR',{minimumFractionDigits:2});
        }

        document.getElementById('tipo-impuesto').addEventListener('change', recalcularTotales);

        // ── Conversión de Moneda Inteligente (Clon del POS) ────────────────
        document.getElementById('moneda').addEventListener('change', async function() {
            const newMoneda = this.value;
            const previousMoneda = this.dataset.prev || 'CRC';

            if (newMoneda !== previousMoneda) {
                const tasaUSD = currentRates.usd > 1 ? currentRates.usd : 520;
                const tasaEUR = currentRates.eur > 1 ? currentRates.eur : 565;

                const result = await Swal.fire({
                    title: '¿Convertir precios?',
                    html: `Has cambiado la moneda de <strong>${previousMoneda}</strong> → <strong>${newMoneda}</strong>.<br><br>
                           <small style="color:#64748b;">Tipo de cambio MH: USD ₡${currentRates.usd.toFixed(2)} | EUR ₡${currentRates.eur.toFixed(2)}</small><br><br>
                           ¿Deseas convertir automáticamente los precios de las líneas usando el tipo de cambio oficial?`,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: '<i class="fas fa-exchange-alt"></i> Sí, convertir',
                    cancelButtonText: 'No, mantener valores',
                    confirmButtonColor: '#1e40af'
                });

                if (result.isConfirmed) {
                    convertirPrecios(previousMoneda, newMoneda);
                }
            }
            this.dataset.prev = newMoneda;
            recalcularTotales();
        });

        function convertirPrecios(from, to) {
            let factor = 1;

            // CRC como moneda base, tasas oficiales de Hacienda (currentRates)
            if      (from === 'CRC' && to === 'USD') factor = 1 / currentRates.usd;
            else if (from === 'CRC' && to === 'EUR') factor = 1 / currentRates.eur;
            else if (from === 'USD' && to === 'CRC') factor = currentRates.usd;
            else if (from === 'EUR' && to === 'CRC') factor = currentRates.eur;
            else if (from === 'USD' && to === 'EUR') factor = currentRates.usd / currentRates.eur;
            else if (from === 'EUR' && to === 'USD') factor = currentRates.eur / currentRates.usd;

            document.querySelectorAll('#detalle-lineas tr:not(#empty-row)').forEach(tr => {
                const precInput = tr.querySelector('.precio-i');
                if (precInput) {
                    precInput.value = (parseFloat(precInput.value) * factor).toFixed(2);
                }
                const discInput = tr.querySelector('.disc-i');
                if (discInput && parseFloat(discInput.value) > 0) {
                    discInput.value = (parseFloat(discInput.value) * factor).toFixed(2);
                }
            });
            recalcularTotales();
        }


        // ── Buscador con Autocomplete conectado al Inventario ───────────────
        (function() {
            const input = document.getElementById('buscar-cabys');
            const dropdown = document.getElementById('cabys-dropdown');

            function cerrarDropdown() {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
            }

            function mostrarDropdown(resultados) {
                dropdown.innerHTML = '';
                if (!resultados.length) {
                    dropdown.innerHTML = '<div style="padding:14px 16px; color:#94a3b8; font-size:0.82rem; text-align:center;"><i class="fas fa-search" style="margin-right:6px;"></i>Sin resultados en el catálogo</div>';
                    dropdown.style.display = 'block';
                    return;
                }

                resultados.forEach(prod => {
                    const item = document.createElement('div');
                    item.style.cssText = 'display:flex; align-items:center; justify-content:space-between; padding:10px 14px; cursor:pointer; border-bottom:1px solid #f1f5f9; transition:background 0.15s;';
                    item.innerHTML = `
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:800; font-size:0.82rem; color:#1e293b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${prod.descripcion || prod.nombre}</div>
                            <div style="font-size:0.68rem; color:#94a3b8; margin-top:2px;">
                                <span style="font-family:monospace; background:#f1f5f9; padding:1px 5px; border-radius:4px;">${prod.cabys || '---'}</span>
                                <span style="margin-left:6px; color:#64748b;">${prod.categoria || ''}</span>
                            </div>
                        </div>
                        <div style="font-weight:900; font-size:0.9rem; color:var(--primary); margin-left:12px; white-space:nowrap;">
                            ₡${(prod.precioVenta || prod.precio || 0).toLocaleString('es-CR')}
                        </div>
                    `;
                    item.addEventListener('mouseenter', () => item.style.background = '#eff6ff');
                    item.addEventListener('mouseleave', () => item.style.background = '');
                    item.addEventListener('mousedown', (e) => {
                        e.preventDefault(); // evitar que el blur cierre primero
                        agregarLinea(prod);
                        input.value = '';
                        cerrarDropdown();
                        Swal.fire({ toast: true, position: 'top-end', icon: 'success',
                            title: (prod.descripcion || prod.nombre) + ' añadido',
                            showConfirmButton: false, timer: 1200 });
                    });
                    dropdown.appendChild(item);
                });
                dropdown.style.display = 'block';
            }

            input.addEventListener('input', function() {
                const q = this.value.trim().toLowerCase();
                if (!q || q.length < 2) { cerrarDropdown(); return; }

                const db = window.muroDB;
                if (!db) return;

                const todos = db.getProductos();
                const resultados = todos.filter(p =>
                    multiWordMatch(`${p.descripcion || ''} ${p.nombre || ''} ${p.cabys || ''} ${p.codigo || ''} ${p.categoria || ''}`, q)
                ).slice(0, 8); // max 8 resultados

                mostrarDropdown(resultados);
            });

            // Enter = seleccionar primer resultado
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const primer = dropdown.querySelector('div[style*="cursor:pointer"]');
                    if (primer) primer.dispatchEvent(new MouseEvent('mousedown'));
                }
                if (e.key === 'Escape') cerrarDropdown();
            });

            // Cerrar al perder foco
            input.addEventListener('blur', () => setTimeout(cerrarDropdown, 150));

            // Cerrar al hacer clic fuera
            document.addEventListener('click', (e) => {
                if (!document.getElementById('cabys-wrapper').contains(e.target)) cerrarDropdown();
            });
        })();


        document.getElementById('edit-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const db = window.muroDB;
            if(!db) return;

            const detalle = [];
            let totalImpuestos = 0;
            let totalDescuentos = 0;
            let totalVentaNeta = 0;
            const tasaIVA = (parseFloat(document.getElementById('tipo-impuesto').value) || 0) / 100;

            document.querySelectorAll('#detalle-lineas tr:not(#empty-row)').forEach(tr => {
                const c = parseFloat(tr.querySelector('.cant-i').value) || 0;
                const p = parseFloat(tr.querySelector('.precio-i').value) || 0;
                const d = parseFloat(tr.querySelector('.disc-i').value) || 0;
                
                const brLinea = c * p;
                const netoLinea = Math.max(brLinea - d, 0);
                const impuestoLinea = netoLinea * tasaIVA;
                
                totalDescuentos += d;
                totalVentaNeta += netoLinea;
                totalImpuestos += impuestoLinea;

                detalle.push({
                    cabys: tr.querySelector('.cabys-i').value,
                    descripcion: tr.querySelector('.desc-i').value,
                    cantidad: c,
                    precio: p,
                    descuento: d,
                    subtotal: netoLinea,
                    impuesto: impuestoLinea
                });
            });

            const totalText = document.getElementById('total-final').textContent;
            const finalMonto = parseFloat(totalText.replace(/[^\d.-]/g, ''));
            const moneda = document.getElementById('moneda').value;
            
            const receptorCustom = {
                nombre: document.getElementById('edit-cli-nombre').value || 'Cliente',
                identificacion: document.getElementById('edit-cli-id').value || '000000000',
                provincia: document.getElementById('edit-cli-prov').value,
                canton: document.getElementById('edit-cli-cant').value,
                correo: document.getElementById('edit-cli-mail').value
            };

            const isDraft = editDoc && editDoc.estado === 'Borrador';
            
            // Función auxiliar para generar Documentos
            const generarDocumentos = (idComprobante, esNotaCredito) => {
                const tipoDoc = esNotaCredito ? "Nota de Crédito" : "Factura Electrónica";
                
                // 1. GENERAR XML
                let lineasXML = '';
                detalle.forEach((item, index) => {
                    const montoTotalLinea = item.cantidad * item.precio;
                    lineasXML += `
                <LineaDetalle>
                    <NumeroLinea>${index + 1}</NumeroLinea>
                    <Codigo>
                        <Tipo>04</Tipo>
                        <Codigo>${item.cabys || '0000000000000'}</Codigo>
                    </Codigo>
                    <Cantidad>${item.cantidad.toFixed(3)}</Cantidad>
                    <UnidadMedida>Unid</UnidadMedida>
                    <Detalle>${item.descripcion}</Detalle>
                    <PrecioUnitario>${item.precio.toFixed(5)}</PrecioUnitario>
                    <MontoTotal>${montoTotalLinea.toFixed(5)}</MontoTotal>
                    ${item.descuento > 0 ? `<Descuento><MontoDescuento>${item.descuento.toFixed(5)}</MontoDescuento><NaturalezaDescuento>Descuento Especial</NaturalezaDescuento></Descuento>` : ''}
                    <SubTotal>${item.subtotal.toFixed(5)}</SubTotal>
                    <Impuesto>
                        <Codigo>01</Codigo>
                        <CodigoTarifa>08</CodigoTarifa>
                        <Tarifa>${(tasaIVA * 100).toFixed(2)}</Tarifa>
                        <Monto>${item.impuesto.toFixed(5)}</Monto>
                    </Impuesto>
                    <MontoTotalLinea>${(item.subtotal + item.impuesto).toFixed(5)}</MontoTotalLinea>
                </LineaDetalle>`;
                });

                const xmlTemplate = `<?xml version="1.0" encoding="utf-8"?>
<${tipoDoc.replace(/\s/g, '')} xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/${esNotaCredito ? 'notaCreditoElectronica' : 'facturaElectronica'}">
    <Clave>50624032400031018975640010000101000000000${Date.now().toString().slice(-9)}</Clave>
    <CodigoActividad>620100</CodigoActividad>
    <NumeroConsecutivo>${idComprobante}</NumeroConsecutivo>
    <FechaEmision>${new Date().toISOString()}</FechaEmision>
    <Emisor>
        <Nombre>MUROTECH SOLUTIONS S.A.</Nombre>
        <Identificacion><Tipo>02</Tipo><Numero>3101897564</Numero></Identificacion>
        <Ubicacion><Provincia>1</Provincia><Canton>01</Canton><Distrito>01</Distrito><OtrasSenas>San José</OtrasSenas></Ubicacion>
    </Emisor>
    <Receptor>
        <Nombre>${receptorCustom.nombre}</Nombre>
        <Identificacion><Tipo>01</Tipo><Numero>${receptorCustom.identificacion}</Numero></Identificacion>
        <CorreoElectronico>${receptorCustom.correo || ''}</CorreoElectronico>
    </Receptor>
    <CondicionVenta>${document.getElementById('condicion-venta').value}</CondicionVenta>
    <MedioPago>${document.getElementById('medio-pago').value}</MedioPago>
    <DetalleServicio>${lineasXML}</DetalleServicio>
    <ResumenFactura>
        <CodigoTipoMoneda>
            <CodigoMoneda>${moneda}</CodigoMoneda>
            <TipoCambio>1.00000</TipoCambio>
        </CodigoTipoMoneda>
        <TotalVenta>${(totalVentaNeta + totalDescuentos).toFixed(5)}</TotalVenta>
        <TotalDescuentos>${totalDescuentos.toFixed(5)}</TotalDescuentos>
        <TotalVentaNeta>${totalVentaNeta.toFixed(5)}</TotalVentaNeta>
        <TotalImpuesto>${totalImpuestos.toFixed(5)}</TotalImpuesto>
        <TotalComprobante>${finalMonto.toFixed(5)}</TotalComprobante>
    </ResumenFactura>
    ${esNotaCredito ? `
    <InformacionReferencia>
        <TipoDoc>01</TipoDoc>
        <Numero>${editDoc ? editDoc.id : 'N/A'}</Numero>
        <FechaEmision>${editDoc ? editDoc.fecha : new Date().toISOString()}</FechaEmision>
        <Codigo>${document.getElementById('ref-codigo').value}</Codigo>
        <Razon>${document.getElementById('ref-razon').value}</Razon>
    </InformacionReferencia>` : ''}
</${tipoDoc.replace(/\s/g, '')}>`;

                const blob = new Blob([xmlTemplate], { type: 'application/xml' });
                const urlXML = URL.createObjectURL(blob);
                const aXML = document.createElement('a');
                aXML.href = urlXML;
                aXML.download = `${tipoDoc.replace(/\s/g, '_')}_${idComprobante}.xml`;
                document.body.appendChild(aXML);
                aXML.click();
                document.body.removeChild(aXML);

                // 2. GENERAR PDF
                try {
                    const { jsPDF } = window.jspdf;
                    const docPDF = new jsPDF();
                    
                    docPDF.setFontSize(22);
                    docPDF.setTextColor(30, 58, 138);
                    docPDF.text("MUROTECH SOLUTIONS S.A.", 14, 22);
                    
                    docPDF.setFontSize(10);
                    docPDF.setTextColor(100, 116, 139);
                    docPDF.text("Cédula Jurídica: 3-101-897564", 14, 28);
                    docPDF.text("San José, Costa Rica | soporte@murotech.cr", 14, 33);
                    docPDF.text(`Fecha: ${new Date().toLocaleDateString('es-CR')} ${new Date().toLocaleTimeString('es-CR')}`, 14, 38);
                    
                    docPDF.setFontSize(14);
                    docPDF.setTextColor(15, 23, 42);
                    docPDF.text(tipoDoc.toUpperCase(), 140, 22);
                    docPDF.setFontSize(10);
                    docPDF.text(`Comprobante: ${idComprobante}`, 140, 28);
                    
                    if (esNotaCredito && editDoc) {
                        docPDF.setTextColor(220, 38, 38);
                        docPDF.text(`Aplica a Factura: ${editDoc.id}`, 140, 33);
                        docPDF.setTextColor(15, 23, 42);
                    }

                    docPDF.setDrawColor(226, 232, 240);
                    docPDF.setFillColor(248, 250, 252);
                    docPDF.roundedRect(14, 45, 182, 35, 3, 3, "FD");
                    docPDF.setFontSize(11);
                    docPDF.text("DATOS DEL RECEPTOR", 18, 52);
                    
                    docPDF.setFontSize(10);
                    docPDF.setTextColor(71, 85, 105);
                    docPDF.text(`Nombre: ${receptorCustom.nombre}`, 18, 60);
                    docPDF.text(`ID/Cédula: ${receptorCustom.identificacion}`, 18, 66);
                    docPDF.text(`Correo: ${receptorCustom.correo || 'N/A'}`, 18, 72);
                    docPDF.text(`Moneda: ${moneda}`, 120, 60);
                    
                    const tableData = detalle.map((d, i) => [i + 1, d.descripcion, d.cantidad, d.precio.toFixed(2), d.subtotal.toFixed(2)]);
                    
                    docPDF.autoTable({
                        startY: 85,
                        head: [['#', 'Descripción', 'Cant', 'P.Unit', 'Neto']],
                        body: tableData,
                        theme: 'grid',
                        headStyles: { fillColor: esNotaCredito ? [220, 38, 38] : [37, 99, 235] },
                        styles: { fontSize: 9 }
                    });
                    
                    const finalY = docPDF.lastAutoTable.finalY + 10;
                    docPDF.setFontSize(10);
                    docPDF.text(`Subtotal Neta: ${monedaSymbols[moneda] || '$'} ${totalVentaNeta.toFixed(2)}`, 140, finalY);
                    docPDF.text(`IVA Estimado: ${monedaSymbols[moneda] || '$'} ${totalImpuestos.toFixed(2)}`, 140, finalY + 6);
                    docPDF.setFontSize(12);
                    docPDF.setTextColor(0, 0, 0);
                    docPDF.text(`TOTAL: ${monedaSymbols[moneda] || '$'} ${finalMonto.toFixed(2)}`, 140, finalY + 16);
                    
                    docPDF.save(`${tipoDoc.replace(/\s/g, '_')}_${idComprobante}.pdf`);
                } catch(err) {
                    console.error("Error PDF:", err);
                }
            };

            if(isDraft) {
                db.updateFactura(editDoc.id, {
                    monto: finalMonto,
                    fecha: document.getElementById('fecha-emision').value,
                    observaciones: document.getElementById('observaciones').value,
                    condicionVenta: document.getElementById('condicion-venta').value,
                    medioPago: document.getElementById('medio-pago').value,
                    moneda: document.getElementById('moneda').value,
                    detalle: detalle,
                    receptor: receptorCustom,
                    estado: 'Emitida'
                });
                generarDocumentos(editDoc.id, false);
                Swal.fire({ title: '¡Borrador Emitido!', text: 'Los documentos XML y PDF han sido generados exitosamente.', icon: 'success' })
                    .then(() => window.location.href = 'panelControl.html');
            } else {
                const newId = 'NC-' + Math.floor(Math.random()*9000 + 1000);
                const newNC = {
                    id: newId,
                    clienteId: document.getElementById('cliente-info-panel').dataset.clienteId,
                    clienteNombre: receptorCustom.nombre,
                    monto: finalMonto,
                    estado: 'Emitida',
                    tipo: 'Nota de Crédito',
                    referencia: editDoc ? editDoc.id : 'N/A',
                    refMotivo: document.getElementById('ref-codigo').value,
                    referenciaRazon: document.getElementById('ref-razon').value,
                    fecha: new Date().toISOString(),
                    detalle: detalle,
                    receptor: receptorCustom,
                    condicionVenta: document.getElementById('condicion-venta').value,
                    medioPago: document.getElementById('medio-pago').value,
                    moneda: document.getElementById('moneda').value
                };
                db.addFactura(newNC);
                generarDocumentos(newId, true);
                Swal.fire({ title: '¡Nota de Crédito Generada!', text: 'Se ha creado el comprobante de corrección con los nuevos XML y PDF.', icon: 'success' })
                    .then(() => window.location.href = 'panelControl.html');
            }
        });

        window.mostrarSelectorComprobantes = function() {
            const db = window.muroDB;
            if(!db) return;
            const facturas = db.getFacturas();
            
            let htmlTable = `
                <div style="padding: 10px 0;">
                    <input type="text" id="filtro-selector" placeholder="Buscar por ID o Cliente..." 
                           style="width: 100%; padding: 14px; border: 1.5px solid #e2e8f0; border-radius: 14px; margin-bottom: 20px; font-family: 'Outfit'; font-weight:600; font-size:0.9rem; outline:none; transition:border 0.2s;">
                </div>
                <div id="selector-table-container" style="max-height: 420px; overflow-y: auto; text-align: left; background: #ffffff; border-radius: 16px; border: 1px solid #f1f5f9;">
                    <table style="width: 100%; border-collapse: collapse; font-family: 'Outfit', sans-serif;">
                        <thead>
                            <tr style="background: #f8fafc; position: sticky; top: 0; border-bottom: 2px solid #e2e8f0;">
                                <th style="padding: 14px; font-size: 0.72rem; font-weight:900; color:#64748b; text-transform:uppercase;">ID</th>
                                <th style="padding: 14px; font-size: 0.72rem; font-weight:900; color:#64748b; text-transform:uppercase;">RECEPTOR / CLIENTE</th>
                                <th style="padding: 14px; font-size: 0.72rem; font-weight:900; color:#64748b; text-transform:uppercase;">ESTADO</th>
                                <th style="padding: 14px; font-size: 0.72rem; font-weight:900; color:#64748b; text-transform:uppercase; text-align:center;">ACCIÓN</th>
                            </tr>
                        </thead>
                        <tbody id="lista-comprobantes">
                            ${facturas.map(f => `
                                <tr class="doc-row" data-search="${f.id} ${f.clienteNombre}" style="border-bottom: 1px solid #f1f5f9; transition:background 0.2s;">
                                    <td style="padding: 14px; font-weight: 800; font-size: 0.85rem; color:#1e293b;">${f.id}</td>
                                    <td style="padding: 14px; font-size: 0.85rem; font-weight:600; color:#475569;">${f.clienteNombre}</td>
                                    <td style="padding: 14px;">
                                        <span style="font-size: 0.65rem; padding: 4px 10px; border-radius: 20px; font-weight: 900; 
                                              background: ${f.estado === 'Borrador' ? '#fef9c3' : (f.estado === 'Pendiente' ? '#e0f2fe' : '#ecfdf5')}; 
                                              color: ${f.estado === 'Borrador' ? '#a16207' : (f.estado === 'Pendiente' ? '#0369a1' : '#10b981')};">
                                            ${f.estado.toUpperCase()}
                                        </span>
                                    </td>
                                    <td style="padding: 14px; text-align:center;">
                                        <button onclick="seleccionarYPasar('${f.id}')" style="background: var(--primary); color: white; border: none; padding: 8px 16px; border-radius: 9px; cursor: pointer; font-size: 0.75rem; font-weight:800; transition:all 0.2s; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                                            EDITAR
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            Swal.fire({
                title: 'Seleccionar Comprobante',
                html: htmlTable,
                width: '740px',
                showConfirmButton: false,
                showCloseButton: true,
                didOpen: () => {
                    const input = document.getElementById('filtro-selector');
                    input.addEventListener('input', (e) => {
                        const q = e.target.value.toLowerCase();
                        document.querySelectorAll('.doc-row').forEach(row => {
                            row.style.display = row.dataset.search.toLowerCase().includes(q) ? '' : 'none';
                        });
                    });
                }
            });
        };

        window.seleccionarYPasar = function(id) {
            const db = window.muroDB;
            const doc = db.getFacturas().find(f => f.id === id);
            if(doc) {
                editDoc = doc;
                const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?id=' + id;
                window.history.pushState({path:newUrl},'',newUrl);
                document.getElementById('detalle-lineas').innerHTML = '';
                lineCount = 0;
                poblarDatosCompleto(doc);
                Swal.close();
                Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Comprobante "' + id + '" cargado', showConfirmButton: false, timer: 1500 });
            }
        };

        const canvas = document.getElementById('particles-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const particles = [];
        class Particle { constructor(){this.x=Math.random()*canvas.width;this.y=Math.random()*canvas.height;this.size=Math.random()*2+0.5;this.speedX=Math.random()*0.5-0.25;this.speedY=Math.random()*0.5-0.25;this.opacity=Math.random()*0.5+0.1;} update(){this.x+=this.speedX;this.y+=this.speedY;if(this.x>canvas.width)this.x=0;if(this.x<0)this.x=canvas.width;if(this.y>canvas.height)this.y=0;if(this.y<0)this.y=canvas.height;} draw(){ctx.fillStyle=`rgba(255,255,255,${this.opacity})`;ctx.beginPath();ctx.arc(this.x,this.y,this.size,0,Math.PI*2);ctx.fill();} }
        for(let i=0;i<60;i++) particles.push(new Particle());
        function animate(){ctx.clearRect(0,0,canvas.width,canvas.height);particles.forEach(p=>{p.update();p.draw();});requestAnimationFrame(animate);}
        animate();