// --- LOGICA DE SIDELAR ---
        if (typeof sidebarRender === 'function') sidebarRender('cotizaciones.html');

        // --- DIVISAS & HACIENDA (Robust Interface) ---
        let currentRates = { usd: 1, eur: 1 };
        const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };

        async function syncRates() {
            const urlDirecta = "https://api.hacienda.go.cr/indicadores/tc";
            const urlProxy = "proxy_hacienda.php";
            let data = null;

            try {
                // Intento 1: Proxy
                const resProxy = await fetch(urlProxy);
                if (resProxy.ok) data = await resProxy.json();
            } catch (e) { console.warn("Proxy no disponible en Cotizaciones..."); }

            if (!data) {
                try {
                    // Intento 2: Directa
                    const resDirecta = await fetch(urlDirecta);
                    if (resDirecta.ok) data = await resDirecta.json();
                } catch (e) { console.error("Fallo total de conexión Hacienda."); }
            }

            if (data) {
                if (data.dolar && data.dolar.venta) {
                    currentRates.usd = data.dolar.venta.valor;
                    document.getElementById('fx-usd-venta').textContent = '₡' + currentRates.usd.toFixed(2);
                }
                if (data.euro) {
                    currentRates.eur = data.euro.colones;
                    document.getElementById('fx-eur-valor').textContent = '₡' + currentRates.eur.toFixed(2);
                }
            }
        }
        syncRates();

        /* ======= MOTOR DE CLIENTES CON AUTOCOMPLETE PREMIUM ======= */
        (function() {
            const input = document.getElementById('buscar-cliente-id');
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

            document.getElementById('btn-buscar-cliente').addEventListener('click', function() {
                const q = input.value.trim().toLowerCase();
                if (!q) { Swal.fire('Atención', 'Ingrese algo para buscar.', 'warning'); return; }
                const db = window.muroDB;
                if (!db) return;
                const clientes = db.getClientes();
                let found = clientes.find(c => c.identificacion.replace(/[-\s]/g, '') === q.replace(/[-\s]/g, ''));
                if (!found) found = clientes.find(c => multiWordMatch(`${c.nombre} ${c.identificacion}`, q));
                if (found) { seleccionarCliente(found); closeDropdown(); }
                else { Swal.fire('No encontrado', 'No se encontró ningún cliente.', 'info'); }
            });

            function seleccionarCliente(cli) {
                document.getElementById('cli-nombre').textContent = cli.nombre;
                document.getElementById('cli-full-id').textContent = `${cli.tipoId} - ${cli.identificacion}`;
                document.getElementById('cli-provincia').textContent = cli.provincia;
                document.getElementById('cli-canton').textContent = cli.canton;
                document.getElementById('cli-distrito').textContent = cli.distrito;
                document.getElementById('cli-email').textContent = cli.email;
                document.getElementById('cli-telefono').textContent = cli.telefono;
                document.getElementById('cli-regimen').textContent = cli.regimen || 'Régimen General';
                document.getElementById('cli-actividad').textContent = cli.actividad || 'Actividad no especificada';

                document.getElementById('cliente-info-panel').classList.add('visible');
                document.getElementById('manual-prospecto').style.display = 'none';
                input.value = cli.identificacion;

                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    icon: 'success',
                    title: 'Cliente: ' + cli.nombre,
                    showConfirmButton: false,
                    timer: 2000
                });
            }

            input.addEventListener('click', (e) => e.stopPropagation());
            dropdown.addEventListener('click', (e) => e.stopPropagation());
            document.addEventListener('click', closeDropdown);
        })();

        // Soporte para Enter en el buscador de cliente
        document.getElementById('buscar-cliente-id').addEventListener('keydown', function(e) {
            if(e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('btn-buscar-cliente').click();
            }
        });

        // --- LINEAS Y PRODUCTOS ---
        let lineCount = 0;
        document.getElementById('btn-add-manual').addEventListener('click', () => agregarLinea());
        
        function agregarLinea(prodData = null) {
            lineCount++;
            const empty = document.getElementById('empty-row');
            if(empty) empty.remove();
            
            const tbody = document.getElementById('detalle-tabla');
            const tr = document.createElement('tr');
            tr.id = 'linea-' + lineCount;
            
            const monedaActual = document.getElementById('moneda').value;
            const symbol = monedaSymbols[monedaActual] || '$';
            
            let precio = 0;
            let descr = "";
            
            if(prodData) {
                precio = prodData.precioVenta || prodData.precio || 0;
                descr = prodData.descripcion || prodData.nombre || "";
                // Conversion inmediata si estamos en USD/EUR
                if(monedaActual === 'USD' && currentRates.usd > 1) precio = precio / currentRates.usd;
                if(monedaActual === 'EUR' && currentRates.eur > 1) precio = precio / currentRates.eur;
            }

            tr.innerHTML = `
                <td><input type="number" class="fi-table cant-i text-center" value="1" min="1" step="1" oninput="recalcular()"></td>
                <td><input type="text" class="fi-table desc-i" value="${descr}" placeholder="Servicio profesional o producto…"></td>
                <td><input type="number" class="fi-table precio-i text-center" value="${precio.toFixed(2)}" step="0.01" oninput="recalcular()"></td>
                <td><input type="number" class="fi-table desc-i text-center" value="0.00" min="0" max="100" step="0.01" oninput="recalcular()"></td>
                <td style="text-align:right;"><span class="sub-cell" style="font-weight:900; color:var(--primary); font-size:1rem;">${symbol}0.00</span></td>
                <td class="text-center">
                    <button type="button" onclick="this.closest('tr').remove(); recalcular();" style="border:none; background:none; color:#ef4444; cursor:pointer; font-size:1.1rem; opacity:0.7; transition:opacity 0.2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
            recalcular();
        }


        // --- MOTOR DE PRODUCTOS CON AUTOCOMPLETE PREMIUM ---
        (function() {
            const input = document.getElementById('buscar-producto');
            const dropdown = document.getElementById('producto-dropdown');

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
                        agregarLinea(prod);
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
                    multiWordMatch(`${p.descripcion || p.nombre} ${p.cabys || ''} ${p.codigo || ''}`, q)
                ).slice(0, 10);
                renderResults(matches);
            });

            // Evitar que el dropdown se cierre al hacer click dentro
            input.addEventListener('click', (e) => e.stopPropagation());
            dropdown.addEventListener('click', (e) => e.stopPropagation());
            document.addEventListener('click', closeDropdown);
        })();


        // --- MOTOR DE CALCULOS ---
        function recalcular() {
            const moneda = document.getElementById('moneda').value;
            const symbol = monedaSymbols[moneda] || '$';
            let gross = 0; let discounts = 0;

            document.querySelectorAll('#detalle-tabla tr:not(#empty-row)').forEach(tr => {
                const inputs = tr.querySelectorAll('input');
                const c = parseFloat(inputs[0].value) || 0;
                const p = parseFloat(inputs[2].value) || 0;
                const dPct = parseFloat(inputs[3].value) || 0;
                
                const lineTotal = c * p;
                const lineDisc = lineTotal * (dPct / 100);
                const neto = lineTotal - lineDisc;
                
                gross += lineTotal;
                discounts += lineDisc;
                
                tr.querySelector('.sub-cell').textContent = symbol + neto.toLocaleString('es-CR', {minimumFractionDigits:2});
            });

            const iva = (gross - discounts) * 0.13;
            const final = (gross - discounts) + iva;

            document.getElementById('total-subtotal').textContent = symbol + gross.toLocaleString('es-CR', {minimumFractionDigits:2});
            document.getElementById('total-descuento').textContent = symbol + discounts.toLocaleString('es-CR', {minimumFractionDigits:2});
            document.getElementById('total-impuesto').textContent = symbol + iva.toLocaleString('es-CR', {minimumFractionDigits:2});
            document.getElementById('total-final').textContent = symbol + final.toLocaleString('es-CR', {minimumFractionDigits:2});
        }

        // --- VALIDEZ Y FECHAS ---
        function updateVencimiento() {
            const dias = parseInt(document.getElementById('validez-dias').value) || 15;
            const fecha = new Date();
            fecha.setDate(fecha.getDate() + dias);
            document.getElementById('fecha-vencimiento').value = fecha.toISOString().split('T')[0];
        }
        document.getElementById('validez-dias').addEventListener('input', updateVencimiento);
        updateVencimiento();

        // Moneda change con confirmacion de conversion
        document.getElementById('moneda').addEventListener('change', async function() {
            const prev = this.dataset.prev || 'CRC';
            const next = this.value;
            if(prev !== next) {
               const res = await Swal.fire({ title: '¿Convertir todos los precios?', text: `Has cambiado a ${next}. ¿Deseas aplicar la tasa de Hacienda a los ítems ya agregados?`, icon: 'question', showCancelButton: true });
               if(res.isConfirmed) {
                    let factor = 1;
                    if(prev === 'CRC' && next === 'USD') factor = 1 / currentRates.usd;
                    else if(prev === 'USD' && next === 'CRC') factor = currentRates.usd;
                    // ... (demas casos)
                    document.querySelectorAll('.precio-i').forEach(inp => {
                        inp.value = (parseFloat(inp.value) * factor).toFixed(2);
                    });
               }
            }
            this.dataset.prev = next;
            recalcular();
        });

        document.getElementById('proforma-form').addEventListener('submit', (e) => {
            e.preventDefault();
            
            const numIdReceptor = document.getElementById('cli-full-id').textContent.trim() || 'Desconocido';
            const nombreReceptor = document.getElementById('cli-nombre').textContent.trim() || 'Prospecto';
            const correoReceptor = document.getElementById('cli-email').textContent.trim();
            const moneda = document.getElementById('moneda').value;
            const notas = document.getElementById('notas-cotizacion').value;
            const vencimiento = document.getElementById('fecha-vencimiento').value;

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
                doc.text("San José, Costa Rica | ventas@murotech.cr", 14, 33);
                doc.text(`Fecha: ${new Date().toLocaleDateString('es-CR')}`, 14, 38);
                
                doc.setFontSize(14);
                doc.setTextColor(15, 23, 42);
                doc.text("COTIZACIÓN / PROFORMA", 140, 22);
                doc.setFontSize(10);
                doc.text(`Válida hasta: ${vencimiento.split('-').reverse().join('/')}`, 140, 28);
                
                // Datos del cliente
                doc.setDrawColor(226, 232, 240);
                doc.setFillColor(248, 250, 252);
                doc.roundedRect(14, 45, 182, 35, 3, 3, "FD");
                doc.setTextColor(15, 23, 42);
                doc.setFontSize(11);
                doc.text("DATOS DEL PROSPECTO/CLIENTE", 18, 52);
                
                doc.setFontSize(10);
                doc.setTextColor(71, 85, 105);
                doc.text(`Nombre: ${nombreReceptor}`, 18, 60);
                doc.text(`ID/Cédula: ${numIdReceptor}`, 18, 66);
                doc.text(`Correo: ${correoReceptor !== '---' ? correoReceptor : 'N/A'}`, 18, 72);
                doc.text(`Moneda: ${moneda}`, 120, 60);
                
                // Filas de la tabla
                const tableData = [];
                document.querySelectorAll('#detalle-tabla tr:not(#empty-row)').forEach((tr, index) => {
                    const inputs = tr.querySelectorAll('input');
                    const c = inputs[0].value;
                    const desc = inputs[1].value;
                    const p = parseFloat(inputs[2].value).toFixed(2);
                    const dPct = inputs[3].value;
                    const subc = tr.querySelector('.sub-cell').textContent.replace(/[^\d.-]/g, '');
                    tableData.push([index + 1, desc, c, p, dPct + '%', subc]);
                });
                
                // Generar Tabla
                doc.autoTable({
                    startY: 85,
                    head: [['#', 'Descripción', 'Cant', 'P.Unit', 'Desc %', 'Neto']],
                    body: tableData,
                    theme: 'grid',
                    headStyles: { fillColor: [37, 99, 235] },
                    styles: { fontSize: 9 }
                });
                
                const finalY = doc.lastAutoTable.finalY + 10;
                
                // Agregar Notas
                if (notas.trim()) {
                    doc.setFontSize(10);
                    doc.setTextColor(15, 23, 42);
                    doc.text("Notas y Condiciones Comerciales:", 14, finalY);
                    doc.setFontSize(9);
                    doc.setTextColor(71, 85, 105);
                    const splitNotas = doc.splitTextToSize(notas, 120);
                    doc.text(splitNotas, 14, finalY + 6);
                }

                // Totales
                doc.setFontSize(10);
                doc.setTextColor(71, 85, 105);
                doc.text(`Subtotal / Bruto: ${document.getElementById('total-subtotal').textContent}`, 140, finalY);
                doc.text(`Descuentos: ${document.getElementById('total-descuento').textContent}`, 140, finalY + 6);
                doc.text(`IVA (Estimado): ${document.getElementById('total-impuesto').textContent}`, 140, finalY + 12);
                doc.setFontSize(12);
                doc.setTextColor(0, 0, 0);
                doc.text(`INVERSIÓN TOTAL: ${document.getElementById('total-final').textContent}`, 140, finalY + 20);
                
                doc.save(`Cotizacion_${nombreReceptor.replace(/\s+/g,'_')}_${Date.now()}.pdf`);
                
                Swal.fire('¡Éxito!', 'La proforma ha sido generada y el documento PDF descargado.', 'success').then(() => {
                    window.location.reload();
                });
            } catch (err) {
                console.error(err);
                Swal.fire('Error', 'Hubo un problema al generar el PDF.', 'error');
            }
        });
    


        const canvas = document.getElementById('particles-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const particles = [];
        class Particle {
            constructor() { 
                this.x = Math.random() * canvas.width; 
                this.y = Math.random() * canvas.height; 
                this.size = Math.random() * 2 + 0.5; 
                this.speedX = Math.random() * 0.5 - 0.25; 
                this.speedY = Math.random() * 0.5 - 0.25; 
                this.opacity = Math.random() * 0.5 + 0.1; 
            }
            update() { 
                this.x += this.speedX; this.y += this.speedY; 
                if(this.x > canvas.width) this.x = 0; if(this.x < 0) this.x = canvas.width; 
                if(this.y > canvas.height) this.y = 0; if(this.y < 0) this.y = canvas.height; 
            }
            draw() { 
                ctx.fillStyle = `rgba(255, 255, 255, ${this.opacity})`; 
                ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fill(); 
            }
        }
        for(let i = 0; i < 70; i++) particles.push(new Particle());
        function animate() { 
            ctx.clearRect(0, 0, canvas.width, canvas.height); 
            particles.forEach(p => { p.update(); p.draw(); }); 
            requestAnimationFrame(animate); 
        }
        animate();
        window.addEventListener('resize', () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; });