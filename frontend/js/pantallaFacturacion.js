(function () {
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
        }

        function limpiarCliente() {
            const ids = ['cli-tipo-id','cli-num-id','cli-nombre','cli-nombre-com',
                         'cli-provincia','cli-canton','cli-distrito','cli-otras-senas',
                         'cli-telefono','cli-email','cli-actividad','cli-regimen'];
            ids.forEach(id => document.getElementById(id).textContent = '–');
            document.getElementById('cliente-info-panel').classList.remove('visible');
            document.getElementById('buscar-cliente-id').value = '';
        }

        /* ======= MOTOR DE CLIENTES CON AUTOCOMPLETE PREMIUM ======= */
        (function() {
            const input = document.getElementById('buscar-cliente-id');
            const dropdown = document.getElementById('cliente-dropdown');
            const tipoIdSelect = document.getElementById('tipo-id-cliente');

            function closeDropdown() {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
            }

            function renderResults(results) {
                dropdown.innerHTML = '';
                if (!results.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron clientes similares</div>';
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
                        seleccionarCliente(cliente);
                        closeDropdown();
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

            // Acción manual (botón buscar)
            document.getElementById('btn-buscar-cliente').addEventListener('click', function() {
                const q = input.value.trim().toLowerCase();
                if (!q) { Swal.fire('Atención', 'Ingrese algo para buscar.', 'warning'); return; }
                
                const db = window.muroDB;
                if (!db) return;
                
                const clientes = db.getClientes();
                let found = clientes.find(c => c.identificacion.replace(/[-\s]/g, '') === q.replace(/[-\s]/g, ''));
                if (!found) {
                    found = clientes.find(c => multiWordMatch(`${c.nombre} ${c.identificacion}`, q));
                }

                if (found) {
                    seleccionarCliente(found);
                    closeDropdown();
                } else {
                    Swal.fire('No encontrado', 'No se encontró ningún cliente con ese criterio.', 'info');
                }
            });

            function seleccionarCliente(cliente) {
                const tiposTexto = {'01':'01 – Cédula Física', '02':'02 – Cédula Jurídica', '03':'03 – DIMEX', '04':'04 – NITE'};
                const dataAdaptada = {
                    tipoId: tiposTexto[cliente.tipoId] || cliente.tipoId,
                    numId: cliente.identificacion,
                    nombre: cliente.nombre,
                    nombreCom: cliente.nombre,
                    provincia: cliente.provincia || 'No registra',
                    canton: cliente.canton || 'No registra',
                    distrito: cliente.distrito || 'No registra',
                    otrasSenas: cliente.barrio ? (cliente.barrio + ', ' + (cliente.direccion||'')) : (cliente.direccion||'No registra'),
                    telefono: cliente.telefono || cliente.movil || 'No registra',
                    email: cliente.correo || 'No registra',
                    actividad: '620100 – Programación Informática',
                    regimen: cliente.regimen === 'general' ? 'Régimen Simplificado / General' : (cliente.regimen || 'General')
                };
                
                tipoIdSelect.value = cliente.tipoId;
                input.value = cliente.identificacion;
                mostrarCliente(dataAdaptada);
            }

            input.addEventListener('click', (e) => e.stopPropagation());
            dropdown.addEventListener('click', (e) => e.stopPropagation());
            document.addEventListener('click', closeDropdown);
        })();

        document.getElementById('btn-limpiar-cliente').addEventListener('click', limpiarCliente);
        document.getElementById('buscar-cliente-id').addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); document.getElementById('btn-buscar-cliente').click(); }
        });

        /* ======= LÓGICA DE DIVISAS (billingFX) ======= */
        let currentRates = { usd: 1, eur: 1 };
        
        async function syncRates() {
            const urlDirecta = "https://api.hacienda.go.cr/indicadores/tc";
            const urlProxy = "proxy_hacienda.php"; 
            
            let data = null;
            
            try {
                // Intento 1: Proxy local
                const resProxy = await fetch(urlProxy);
                if (resProxy.ok) data = await resProxy.json();
            } catch (e) { 
                console.warn("Proxy no disponible en Facturación, intentando API directa..."); 
            }

            if (!data) {
                try {
                    // Intento 2: API Directa
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
        syncRates();

        const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };
        
        document.getElementById('moneda').addEventListener('change', async function() {
            const newMoneda = this.value;
            const previousMoneda = this.dataset.prev || 'CRC';
            
            if (newMoneda !== previousMoneda) {
                const result = await Swal.fire({
                    title: '¿Convertir precios?',
                    text: `Has cambiado la moneda a ${newMoneda}. ¿Deseas convertir automáticamente los precios de las líneas existentes usando el tipo de cambio oficial?`,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, convertir',
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
            const lineas = document.querySelectorAll('#detalle-lineas tr:not(#empty-row)');
            let factor = 1;

            // Lógica simple de conversión basada en CRC como base
            if (from === 'CRC' && to === 'USD') factor = 1 / currentRates.usd;
            else if (from === 'CRC' && to === 'EUR') factor = 1 / currentRates.eur;
            else if (from === 'USD' && to === 'CRC') factor = currentRates.usd;
            else if (from === 'EUR' && to === 'CRC') factor = currentRates.eur;
            else if (from === 'USD' && to === 'EUR') factor = currentRates.usd / currentRates.eur;
            else if (from === 'EUR' && to === 'USD') factor = currentRates.eur / currentRates.usd;

            lineas.forEach(tr => {
                const precInput = tr.querySelector('.precio-item');
                if (precInput) {
                    precInput.value = (parseFloat(precInput.value) * factor).toFixed(2);
                }
                const descInput = tr.querySelector('.desc-item-val');
                if (descInput) {
                    descInput.value = (parseFloat(descInput.value) * factor).toFixed(2);
                }
            });
        }

        /* Sincronizar tarifa al seleccionar tipo de impuesto */
        const tarifas = {
            '01_13': 13, '01_08': 8, '01_04': 4, '01_02': 2, '01_01': 1, '01_00': 0,
            '02': 0, '03': 0, '04': 0, '05': 0, '06': 0, '07': 0, '08': 13, '99': 0
        };

        /* Agregar líneas de detalle */
        let lineCount = 0;
        document.getElementById('btn-agregar-linea').addEventListener('click', function () {
            agregarLineaBlanca();
        });

        function agregarLineaBlanca() {
            lineCount++;
            const empty = document.getElementById('empty-row');
            if (empty) empty.remove();
            const tbody = document.getElementById('detalle-lineas');
            const tr = document.createElement('tr');
            tr.id = 'linea-' + lineCount;
            tr.innerHTML = `
                <td style="color:#94a3b8; font-weight:800; font-size:0.78rem;">#${lineCount}</td>
                <td><input type="text" class="cabys-code" placeholder="000000000" maxlength="13"></td>
                <td><input type="text" class="desc-item" placeholder="Descripción del bien o servicio…"></td>
                <td><input type="number" class="cant-item" value="1" min="1" step="1" style="width:60px;" oninput="recalcularTotales()"></td>
                <td><input type="number" class="precio-item" value="0.00" min="0" step="0.01" oninput="recalcularTotales()"></td>
                <td><input type="number" class="desc-item-val" value="0.00" min="0" step="0.01" oninput="recalcularTotales()"></td>
                <td style="font-weight:800; color:#1e40af;" class="subtotal-cell">₡0.00</td>
                <td><button type="button" class="btn-del" onclick="eliminarLinea('linea-${lineCount}')"><i class="fas fa-trash-alt"></i></button></td>
            `;
            tbody.appendChild(tr);
            recalcularTotales();
        }


        /* ======= MOTOR DE PRODUCTOS CON AUTOCOMPLETE PREMIUM ======= */
        (function() {
            const input = document.getElementById('buscar-cabys');
            const dropdown = document.getElementById('cabys-dropdown');

            function closeDropdown() {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
            }

            function renderResults(results) {
                dropdown.innerHTML = '';
                if (!results.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron productos</div>';
                    dropdown.style.display = 'block';
                    return;
                }

                results.forEach(prod => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `
                        <div class="autocomplete-info">
                            <div class="autocomplete-name">${prod.descripcion || prod.nombre}</div>
                            <div class="autocomplete-subinfo">
                                <span class="autocomplete-badge">${prod.cabys || '00000000'}</span>
                                <span>${prod.barcode || ''}</span>
                            </div>
                        </div>
                        <div class="autocomplete-price">${monedaSymbols[document.getElementById('moneda').value] || '$'}${ (prod.precioVenta || prod.precio || 0).toLocaleString('es-CR') }</div>
                    `;
                    item.onclick = () => {
                        agregarLineaProducto(prod);
                        input.value = '';
                        closeDropdown();
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
                const matches = db.getProductos().filter(p => 
                    multiWordMatch(`${p.descripcion || p.nombre || ''} ${p.cabys || ''} ${p.codigo || ''} ${p.barcode || ''}`, q)
                ).slice(0, 10);
                renderResults(matches);
            });

            // Evitar que el dropdown se cierre al hacer click dentro
            input.addEventListener('click', (e) => e.stopPropagation());
            dropdown.addEventListener('click', (e) => e.stopPropagation());
            document.addEventListener('click', closeDropdown);
        })();


        function agregarLineaProducto(prod) {
            lineCount++;
            const empty = document.getElementById('empty-row');
            if (empty) empty.remove();
            
            const tbody = document.getElementById('detalle-lineas');
            const tr = document.createElement('tr');
            tr.id = 'linea-' + lineCount;
            
            // --- Conversión Inteligente al Agregar ---
            const monedaActual = document.getElementById('moneda').value;
            const symbol = monedaSymbols[monedaActual] || '$';
            
            let precioFinal = prod.precioVenta !== undefined ? prod.precioVenta : prod.precio;
            
            // Si la factura no es en Colones, convertir el precio del inventario (que está en CRC)
            if (monedaActual === 'USD' && currentRates.usd > 1) {
                precioFinal = precioFinal / currentRates.usd;
            } else if (monedaActual === 'EUR' && currentRates.eur > 1) {
                precioFinal = precioFinal / currentRates.eur;
            }

            const precioStr = parseFloat(precioFinal || 0).toFixed(2);
            const cabysStr = prod.cabys || '';
            const descrStr = prod.descripcion || prod.nombre || '';
            
            tr.innerHTML = `
                <td style="color:#94a3b8; font-weight:800; font-size:0.78rem;">#${lineCount}</td>
                <td><input type="text" class="cabys-code" value="${cabysStr}" placeholder="000000000" maxlength="13"></td>
                <td><input type="text" class="desc-item" value="${descrStr}" placeholder="Descripción del bien o servicio…"></td>
                <td><input type="number" class="cant-item" value="1" min="1" step="1" style="width:60px;" oninput="recalcularTotales()"></td>
                <td><input type="number" class="precio-item" value="${precioStr}" min="0" step="0.01" oninput="recalcularTotales()"></td>
                <td><input type="number" class="desc-item-val" value="0.00" min="0" step="0.01" oninput="recalcularTotales()"></td>
                <td style="font-weight:800; color:#1e40af;" class="subtotal-cell">${symbol}0.00</td>
                <td><button type="button" class="btn-del" onclick="eliminarLinea('linea-${lineCount}')"><i class="fas fa-trash-alt"></i></button></td>
            `;
            tbody.appendChild(tr);
            recalcularTotales();
        }

        window.eliminarLinea = function (id) {
            const tr = document.getElementById(id);
            if (tr) tr.remove();
            if (!document.querySelector('#detalle-lineas tr:not(#empty-row)')) {
                const tbody = document.getElementById('detalle-lineas');
                const r = document.createElement('tr');
                r.id = 'empty-row';
                r.innerHTML = `<td colspan="8" style="text-align:center; padding:28px; color:#94a3b8; font-weight:500;"><i class="fas fa-box-open" style="font-size:1.4rem; margin-bottom:6px; display:block;"></i>No hay líneas agregadas</td>`;
                tbody.appendChild(r);
            }
            recalcularTotales();
        };

        function recalcularTotales() {
            try {
                let totalVenta = 0;       // Suma de (Cant * Precio) sin descuentos
                let totalDescuentos = 0;  // Suma de descuentos aplicados
                
                const lineas = document.querySelectorAll('#detalle-lineas tr:not(#empty-row)');
                const moneda = document.getElementById('moneda').value;
                const symbol = monedaSymbols[moneda] || '$';

                lineas.forEach(tr => {
                    const cant = parseFloat(tr.querySelector('.cant-item')?.value) || 0;
                    const prec = parseFloat(tr.querySelector('.precio-item')?.value) || 0;
                    const desc = parseFloat(tr.querySelector('.desc-item-val')?.value) || 0;
                    
                    const subtotalLinea = cant * prec;
                    const netoLinea = Math.max(subtotalLinea - desc, 0);
                    
                    totalVenta += subtotalLinea;
                    totalDescuentos += desc;
                    
                    const cell = tr.querySelector('.subtotal-cell');
                    if (cell) {
                        cell.textContent = `${symbol}${netoLinea.toLocaleString('es-CR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                    }
                });

                // --- Cálculos Globales con Redondeo de Hacienda (2 decimales) ---
                const tasaIVA = (parseFloat(document.getElementById('porcentaje-impuesto')?.value) || 0) / 100;
                const totalVentaNeta = Math.max(totalVenta - totalDescuentos, 0);
                const montoImpuesto = Math.round((totalVentaNeta * tasaIVA) * 100) / 100;
                const totalComprobante = Math.round((totalVentaNeta + montoImpuesto) * 100) / 100;

                // Actualizar UI
                const format = (val) => `${symbol}${val.toLocaleString('es-CR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                
                const elSub = document.getElementById('total-subtotal');
                const elDesc = document.getElementById('total-descuento');
                const elImp = document.getElementById('total-impuesto');
                const elTotal = document.getElementById('total-final');

                if (elSub) elSub.textContent = format(totalVenta);
                if (elDesc) elDesc.textContent = format(totalDescuentos);
                if (elImp) elImp.textContent = format(montoImpuesto);
                if (elTotal) elTotal.textContent = format(totalComprobante);
                
            } catch (err) {
                console.error("Error en motor de cálculo:", err);
            }
        }

        /* ======= GENERACIÓN DE XML v4.4 ======= */
        document.getElementById('factura-form').addEventListener('submit', function (e) {
            e.preventDefault();
            
            try {
                const lineas = document.querySelectorAll('#detalle-lineas tr:not(#empty-row)');
                if (lineas.length === 0) {
                    Swal.fire('Error', 'Debe agregar al menos una línea de detalle.', 'error');
                    return;
                }

                // --- Receptor ---
                const numIdReceptor = document.getElementById('cli-num-id').textContent.trim();
                const nombreReceptor = document.getElementById('cli-nombre').textContent.trim();
                const correoReceptor = document.getElementById('cli-email').textContent.trim();
                const tipoIdRaw = document.getElementById('cli-tipo-id').textContent.trim();

                if (numIdReceptor === '–' || !numIdReceptor) {
                    Swal.fire('Atención', 'Debe seleccionar un cliente válido.', 'warning');
                    return;
                }

                // --- XML Logic ---
                const fechaEmision = new Date().toISOString();
                const condicionVenta = document.getElementById('condicion-venta').value;
                const medioPago = document.getElementById('medio-pago').value;
                const moneda = document.getElementById('moneda').value;
                const porcentajeImpuestoGlobal = parseFloat(document.getElementById('porcentaje-impuesto').value) || 0;

                let lineasXML = '';
                let totalServGravados = 0, totalServExentos = 0, totalMercGravadas = 0, totalMercExentas = 0;
                let totalDescuentos = 0, totalImpuestos = 0;

                lineas.forEach((tr, index) => {
                    const cabys = tr.querySelector('.cabys-code').value || '0000000000000';
                    const detalle = tr.querySelector('.desc-item').value || 'Sin descripción';
                    const cantidad = parseFloat(tr.querySelector('.cant-item').value) || 0;
                    const precioUnit = parseFloat(tr.querySelector('.precio-item').value) || 0;
                    const montoDesc = parseFloat(tr.querySelector('.desc-item-val').value) || 0;
                    
                    const montoTotalLinea = cantidad * precioUnit;
                    const subTotalLinea = montoTotalLinea - montoDesc;
                    const impuestoLinea = subTotalLinea * (porcentajeImpuestoGlobal / 100);
                    const montoTotalLineaFinal = subTotalLinea + impuestoLinea;
                    
                    totalDescuentos += montoDesc;
                    totalImpuestos += impuestoLinea;
                    
                    if (detalle.toLowerCase().includes('servicio')) {
                        if (porcentajeImpuestoGlobal > 0) totalServGravados += subTotalLinea;
                        else totalServExentos += subTotalLinea;
                    } else {
                        if (porcentajeImpuestoGlobal > 0) totalMercGravadas += subTotalLinea;
                        else totalMercExentas += subTotalLinea;
                    }

                    lineasXML += `
                <LineaDetalle>
                    <NumeroLinea>${index + 1}</NumeroLinea>
                    <Codigo>
                        <Tipo>04</Tipo>
                        <Codigo>${cabys}</Codigo>
                    </Codigo>
                    <Cantidad>${cantidad.toFixed(3)}</Cantidad>
                    <UnidadMedida>Unid</UnidadMedida>
                    <Detalle>${detalle}</Detalle>
                    <PrecioUnitario>${precioUnit.toFixed(5)}</PrecioUnitario>
                    <MontoTotal>${montoTotalLinea.toFixed(5)}</MontoTotal>
                    ${montoDesc > 0 ? `<Descuento><MontoDescuento>${montoDesc.toFixed(5)}</MontoDescuento><NaturalezaDescuento>Descuento</NaturalezaDescuento></Descuento>` : ''}
                    <SubTotal>${subTotalLinea.toFixed(5)}</SubTotal>
                    <Impuesto>
                        <Codigo>01</Codigo>
                        <CodigoTarifa>08</CodigoTarifa>
                        <Tarifa>${porcentajeImpuestoGlobal.toFixed(2)}</Tarifa>
                        <Monto>${impuestoLinea.toFixed(5)}</Monto>
                    </Impuesto>
                    <MontoTotalLinea>${montoTotalLineaFinal.toFixed(5)}</MontoTotalLinea>
                </LineaDetalle>`;
                });

                const totalVenta = totalServGravados + totalServExentos + totalMercGravadas + totalMercExentas;
                const montoTotal = totalVenta + totalImpuestos;

                const xmlTemplate = `<?xml version="1.0" encoding="utf-8"?>
<FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica">
    <Clave>50624032400031018975640010000101000000000123456789</Clave>
    <CodigoActividad>620100</CodigoActividad>
    <NumeroConsecutivo>00100001010000000001</NumeroConsecutivo>
    <FechaEmision>${fechaEmision}</FechaEmision>
    <Emisor>
        <Nombre>MUROTECH SOLUTIONS S.A.</Nombre>
        <Identificacion><Tipo>02</Tipo><Numero>3101897564</Numero></Identificacion>
        <Ubicacion>
            <Provincia>1</Provincia><Canton>01</Canton><Distrito>01</Distrito>
            <OtrasSenas>San José, Costa Rica</OtrasSenas>
        </Ubicacion>
    </Emisor>
    <Receptor>
        <Nombre>${nombreReceptor}</Nombre>
        <Identificacion>
            <Tipo>${tipoIdRaw.substring(0, 2) || '01'}</Tipo>
            <Numero>${numIdReceptor}</Numero>
        </Identificacion>
        <CorreoElectronico>${correoReceptor !== 'No registra' ? correoReceptor : ''}</CorreoElectronico>
    </Receptor>
    <CondicionVenta>${condicionVenta}</CondicionVenta>
    <PlazoCredito>${document.getElementById('plazo-credito').value || '0'}</PlazoCredito>
    <MedioPago>${medioPago}</MedioPago>
    <DetalleServicio>${lineasXML}</DetalleServicio>
    <ResumenFactura>
        <CodigoTipoMoneda>
            <CodigoMoneda>${moneda}</CodigoMoneda>
            <TipoCambio>${moneda === 'CRC' ? '1.00000' : (moneda === 'USD' ? currentRates.usd.toFixed(5) : currentRates.eur.toFixed(5))}</TipoCambio>
        </CodigoTipoMoneda>
        <TotalServGravados>${totalServGravados.toFixed(5)}</TotalServGravados>
        <TotalServExentos>${totalServExentos.toFixed(5)}</TotalServExentos>
        <TotalMercanciasGravadas>${totalMercGravadas.toFixed(5)}</TotalMercanciasGravadas>
        <TotalMercanciasExentas>${totalMercExentas.toFixed(5)}</TotalMercanciasExentas>
        <TotalGravado>${(totalServGravados + totalMercGravadas).toFixed(5)}</TotalGravado>
        <TotalExento>${(totalServExentos + totalMercExentas).toFixed(5)}</TotalExento>
        <TotalVenta>${totalVenta.toFixed(5)}</TotalVenta>
        <TotalDescuentos>${totalDescuentos.toFixed(5)}</TotalDescuentos>
        <TotalVentaNeta>${totalVenta.toFixed(5)}</TotalVentaNeta>
        <TotalImpuesto>${totalImpuestos.toFixed(5)}</TotalImpuesto>
        <TotalComprobante>${montoTotal.toFixed(5)}</TotalComprobante>
    </ResumenFactura>
</FacturaElectronica>`;

                const blob = new Blob([xmlTemplate], { type: 'application/xml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Factura_${numIdReceptor}_${Date.now()}.xml`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                // --- Generación Automática de PDF (jsPDF) ---
                try {
                    const { jsPDF } = window.jspdf;
                    const doc = new jsPDF();
                    
                    // Encabezado
                    doc.setFontSize(22);
                    doc.setTextColor(30, 58, 138); // Azul marino
                    doc.text("MUROTECH SOLUTIONS S.A.", 14, 22);
                    
                    doc.setFontSize(10);
                    doc.setTextColor(100, 116, 139);
                    doc.text("Cédula Jurídica: 3-101-897564", 14, 28);
                    doc.text("San José, Costa Rica | facturacion@murotech.cr", 14, 33);
                    doc.text(`Fecha: ${new Date().toLocaleDateString('es-CR')} ${new Date().toLocaleTimeString('es-CR')}`, 14, 38);
                    
                    doc.setFontSize(14);
                    doc.setTextColor(15, 23, 42);
                    doc.text("FACTURA ELECTRÓNICA", 140, 22);
                    doc.setFontSize(10);
                    doc.text(`Comprobante N°: 00100001010000000001`, 120, 28);
                    
                    // Datos del cliente
                    doc.setDrawColor(226, 232, 240);
                    doc.setFillColor(248, 250, 252);
                    doc.roundedRect(14, 45, 182, 35, 3, 3, "FD");
                    doc.setTextColor(15, 23, 42);
                    doc.setFontSize(11);
                    doc.text("DATOS DEL RECEPTOR", 18, 52);
                    
                    doc.setFontSize(10);
                    doc.setTextColor(71, 85, 105);
                    doc.text(`Nombre: ${nombreReceptor}`, 18, 60);
                    doc.text(`ID/Cédula: ${numIdReceptor}`, 18, 66);
                    doc.text(`Correo: ${correoReceptor !== 'No registra' ? correoReceptor : 'N/A'}`, 18, 72);
                    doc.text(`Moneda: ${moneda}`, 120, 60);
                    doc.text(`Condición: Crédito/Contado`, 120, 66);
                    
                    // Filas de la tabla (Extracción rápida)
                    const tableData = [];
                    lineas.forEach((tr, index) => {
                        const cant = tr.querySelector('.cant-item').value;
                        const desc = tr.querySelector('.desc-item').value;
                        const pUnit = tr.querySelector('.precio-item').value;
                        const subT = parseFloat(cant * pUnit).toFixed(2);
                        tableData.push([index + 1, desc, cant, pUnit, subT]);
                    });
                    
                    doc.autoTable({
                        startY: 85,
                        head: [['#', 'Descripción', 'Cant', 'P.Unitario', 'Subtotal']],
                        body: tableData,
                        theme: 'grid',
                        headStyles: { fillColor: [37, 99, 235] },
                        styles: { fontSize: 9 }
                    });
                    
                    // Totales
                    const finalY = doc.lastAutoTable.finalY + 10;
                    doc.setFontSize(10);
                    doc.text(`Subtotal: ${monedaSymbols[moneda] || '$'} ${totalVenta.toFixed(2)}`, 140, finalY);
                    doc.text(`Descuentos: ${monedaSymbols[moneda] || '$'} ${totalDescuentos.toFixed(2)}`, 140, finalY + 6);
                    doc.text(`Impuestos: ${monedaSymbols[moneda] || '$'} ${totalImpuestos.toFixed(2)}`, 140, finalY + 12);
                    doc.setFontSize(12);
                    doc.setTextColor(0, 0, 0);
                    doc.text(`TOTAL FACTURA: ${monedaSymbols[moneda] || '$'} ${montoTotal.toFixed(2)}`, 140, finalY + 20);
                    
                    doc.save(`Factura_${numIdReceptor}_${Date.now()}.pdf`);
                } catch (pdfErr) {
                    console.error("Error generando PDF:", pdfErr);
                }
                
                Swal.fire('¡Éxito!', 'Factura emitida correctamente. Se han generado los documentos XML y PDF.', 'success').then(() => {
                    if (window.muroDB) {
                        const facturas = window.muroDB.getFacturas() || [];
                        facturas.unshift({
                            id: 'FAC-' + Date.now(),
                            clienteNombre: nombreReceptor,
                            monto: montoTotal,
                            estado: 'Pagada',
                            fecha: fechaEmision
                        });
                        localStorage.setItem('murotech_mockdb_v2', JSON.stringify({
                            ...JSON.parse(localStorage.getItem('murotech_mockdb_v2') || '{}'),
                            facturas: facturas
                        }));
                    }
                    window.location.reload();
                });
            } catch (err) {
                console.error(err);
                Swal.fire('Error crítico', err.message, 'error');
            }
        });

        /* ======= EVENTOS DE IMPUESTOS Y CALCULOS ======= */
        const elTipoImp = document.getElementById('tipo-impuesto');
        const elPorcImp = document.getElementById('porcentaje-impuesto');

        if (elTipoImp) {
            elTipoImp.addEventListener('change', function () {
                const val = this.value;
                const pct = tarifas[val];
                if (elPorcImp && pct !== undefined) {
                    elPorcImp.value = pct;
                }
                recalcularTotales();
            });
        }

        if (elPorcImp) {
            elPorcImp.addEventListener('input', recalcularTotales);
            elPorcImp.addEventListener('change', recalcularTotales);
        }

        /* Ejecución inicial */
        recalcularTotales();
    })();

    // Hacer accesibles para onclick y otros
    window.recalcularTotales = recalcularTotales;
    window.agregarLineaBlanca = agregarLineaBlanca;
    window.agregarLineaProducto = agregarLineaProducto;
    window.eliminarLinea = eliminarLinea;
    
    


        const canvas = document.getElementById('particles-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        const particles = [];
        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 1;
                this.speedX = Math.random() * 1.5 - 0.75;
                this.speedY = Math.random() * 1.5 - 0.75;
                this.opacity = Math.random() * 0.5 + 0.2;
            }
            update() {
                this.x += this.speedX; this.y += this.speedY;
                if (this.x > canvas.width) this.x = 0;
                if (this.x < 0) this.x = canvas.width;
                if (this.y > canvas.height) this.y = 0;
                if (this.y < 0) this.y = canvas.height;
            }
            draw() {
                ctx.fillStyle = `rgba(255,255,255,${this.opacity})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        for (let i = 0; i < 60; i++) particles.push(new Particle());
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => { p.update(); p.draw(); });
            particles.forEach((p1, index) => {
                particles.slice(index + 1).forEach(p2 => {
                    const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
                    if (dist < 150) {
                        ctx.strokeStyle = `rgba(255,255,255,${0.1 * (1 - dist / 150)})`;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(p1.x, p1.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.stroke();
                    }
                });
            });
            requestAnimationFrame(animate);
        }
        animate();
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });