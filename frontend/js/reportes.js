(function() {
            // Instancias de Gráficos
            let chartVentas = null;
            let chartPie = null;

            // --- Utilidades ---
            function fmt(n) { 
                return new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', minimumFractionDigits: 0 }).format(n || 0);
            }

            // --- Lógica de Tabs ---
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
                    this.classList.add('active');
                    document.getElementById('tab-' + this.dataset.tab).classList.add('active');
                    
                    // Si se cambia a ventas, re-animar gráficos si es necesario
                    if (this.dataset.tab === 'ventas') {
                        setTimeout(initCharts, 100);
                    }
                });
            });


            // --- Sistema de Búsqueda de Clientes Premium ---
            (function() {
                const searchInput = document.getElementById('filter-cliente-search');
                const idInput = document.getElementById('filter-cliente-id');
                const dropdown = document.getElementById('report-cliente-dropdown');

                searchInput.addEventListener('input', function() {
                    const q = this.value.trim().toLowerCase();
                    if (!q) {
                        idInput.value = 'all';
                        dropdown.style.display = 'none';
                        return;
                    }

                    const db = window.muroDB;
                    const clientes = db ? db.getClientes() : [];
                    const matches = clientes.filter(c => 
                        multiWordMatch(`${c.nombre} ${c.identificacion} ${c.correo || ''} ${c.telefono || ''}`, q)
                    );

                    dropdown.innerHTML = '';
                    if (matches.length > 0) {
                        matches.slice(0, 5).forEach(c => {
                            const div = document.createElement('div');
                            div.className = 'autocomplete-item';
                            div.innerHTML = `
                                <div class="autocomplete-info">
                                    <div class="autocomplete-name">${c.nombre}</div>
                                    <div class="autocomplete-subinfo">${c.identificacion}</div>
                                </div>
                            `;
                            div.onclick = () => {
                                searchInput.value = c.nombre;
                                idInput.value = c.id;
                                dropdown.style.display = 'none';
                            };
                            dropdown.appendChild(div);
                        });
                        dropdown.style.display = 'block';
                    } else {
                        dropdown.style.display = 'none';
                    }
                });

                document.addEventListener('click', (e) => {
                    if (!searchInput.contains(e.target)) dropdown.style.display = 'none';
                });
            })();


            // --- PROCESAMIENTO DE REPORTES ---
            function generateReport() {
                const db = window.muroDB;
                if (!db) return;

                const facturas = db.getFacturas();
                const inventario = db.getProductos();
                
                // 1. Filtrado por período (simulación)
                const filteredFacturas = facturas; // Por ahora tomamos todas
                
                // 2. Cálculo de KPIs
                const totalVentasBrutas = filteredFacturas.reduce((s, f) => s + f.monto, 0);
                const totalIVA = totalVentasBrutas * 0.13;
                
                // Mock de compras (gastos)
                const totalCompras = totalVentasBrutas * 0.45; 
                const utilidad = totalVentasBrutas - totalCompras - (totalVentasBrutas * 0.10);

                document.getElementById('val-ventas').textContent = fmt(totalVentasBrutas);
                document.getElementById('val-compras').textContent = fmt(totalCompras);
                document.getElementById('val-utilidad').textContent = fmt(utilidad);
                document.getElementById('val-impuestos').textContent = fmt(totalIVA);

                // 3. Render Ventas
                const tbodyVentas = document.getElementById('tbody-ventas');
                if (filteredFacturas.length > 0) {
                    tbodyVentas.innerHTML = filteredFacturas.map(f => `
                        <tr>
                            <td>${new Date(f.fecha).toLocaleDateString()}</td>
                            <td style="font-family:monospace; font-weight:700; font-size:0.75rem;">${f.id}</td>
                            <td>${f.clienteNombre || 'Consumidor Final'}</td>
                            <td>${fmt(f.monto * 0.87)}</td>
                            <td>${fmt(f.monto * 0.13)}</td>
                            <td style="font-weight:700; color:var(--rep-accent);">${fmt(f.monto)}</td>
                            <td><span class="stat-badge status-aceptado">${f.estado}</span></td>
                        </tr>
                    `).join('');
                }

                // 3.5 Render Compras (NEW)
                const tbodyCompras = document.getElementById('tbody-compras');
                const compras = db.getCompras ? db.getCompras() : [];
                if (compras.length > 0) {
                    tbodyCompras.innerHTML = compras.map(c => `
                        <tr>
                            <td>${new Date(c.fecha).toLocaleDateString()}</td>
                            <td style="font-weight:700;">${c.proveedor}</td>
                            <td>${c.concepto}</td>
                            <td>${fmt(c.montoNeto)}</td>
                            <td>${fmt(c.iva)}</td>
                            <td style="font-weight:700;">${fmt(c.total)}</td>
                            <td><span class="badge b-info">${c.categoria}</span></td>
                        </tr>
                    `).join('');
                }

                // 4. Render Inventario
                const tbodyInv = document.getElementById('tbody-inventario');
                let valorInv = 0;
                let stockBajo = 0;
                
                tbodyInv.innerHTML = inventario.map(p => {
                    const stock = p.stock || 0;
                    valorInv += ((p.precioVenta || 0) * stock);
                    if (stock < 10) stockBajo++;
                    
                    const status = stock <= 5 ? 'status-error' : (stock <= 15 ? 'status-pendiente' : 'status-aceptado');
                    const statusTxt = stock <= 5 ? 'Crítico' : (stock <= 15 ? 'Bajo' : 'Optimo');

                    return `
                        <tr>
                            <td style="font-family:monospace; font-size:0.75rem;">${p.codigo}</td>
                            <td>${p.descripcion}</td>
                            <td><span class="badge b-info">${p.categoria || 'Genérico'}</span></td>
                            <td>${fmt(p.precio)}</td>
                            <td style="font-weight:700;">${fmt(p.precioVenta)}</td>
                            <td style="font-weight:800; text-align:center;">${stock}</td>
                            <td><span class="stat-badge ${status}">${statusTxt}</span></td>
                        </tr>
                    `;
                }).join('');

                document.getElementById('val-sku-total').textContent = inventario.length;
                document.getElementById('val-stock-economico').textContent = fmt(valorInv);
                document.getElementById('val-stock-bajo').textContent = stockBajo;

                // 5. Render Comprobantes Hacienda
                document.getElementById('tbody-comprobantes').innerHTML = filteredFacturas.map(f => `
                    <tr>
                        <td style="font-family:monospace;font-size:0.7rem;">${f.id}</td>
                        <td>${new Date(f.fecha).toLocaleString()}</td>
                        <td>${f.clienteNombre || 'Publico General'}</td>
                        <td><span class="stat-badge status-aceptado">Aceptado <i class="fas fa-check"></i></span></td>
                        <td style="font-family:monospace; font-size:0.65rem; color:#64748b;">506${Math.random().toString().slice(2,21)}</td>
                        <td><button class="btn-action btn-outline" style="padding:4px 10px; font-size:0.65rem;">Ver XML</button></td>
                    </tr>
                `).join('');

                // 6. Render Cotizaciones (NEW)
                const tbodyCot = document.getElementById('tbody-cotizaciones');
                const cotizaciones = db.getCotizaciones ? db.getCotizaciones() : [];
                if (cotizaciones.length > 0) {
                    tbodyCot.innerHTML = cotizaciones.map(c => `
                        <tr>
                            <td>${new Date(c.fecha).toLocaleDateString()}</td>
                            <td style="font-weight:700; font-family:monospace;">${c.id}</td>
                            <td>${c.clienteNombre}</td>
                            <td>${new Date(c.vencimiento).toLocaleDateString()}</td>
                            <td style="font-weight:700;">${fmt(c.monto)}</td>
                            <td><span class="stat-badge ${c.estado === 'Aceptada' ? 'status-aceptado' : 'status-pendiente'}">${c.estado}</span></td>
                        </tr>
                    `).join('');
                }

                initCharts();
            }

            // --- Visualización con Chart.js ---
            function initCharts() {
                if (chartVentas) chartVentas.destroy();
                if (chartPie) chartPie.destroy();

                const db = window.muroDB;
                const facturas = db.getFacturas();
                
                // Agrupamos ventas por mes (simulado con la fecha real de las facturas)
                const monthlySales = new Array(12).fill(0);
                facturas.forEach(f => {
                    const date = new Date(f.fecha);
                    if (!isNaN(date)) monthlySales[date.getMonth()] += (f.monto / 1000); // K ₡
                });

                const ctxV = document.getElementById('chart-ventas').getContext('2d');
                chartVentas = new Chart(ctxV, {
                    type: 'line',
                    data: {
                        labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
                        datasets: [{
                            label: 'Ingresos Mensuales (K ₡)',
                            data: monthlySales,
                            borderColor: '#1e40af',
                            backgroundColor: 'rgba(30, 64, 175, 0.1)',
                            fill: true,
                            tension: 0.4,
                            borderWidth: 3,
                            pointRadius: 4,
                            pointBackgroundColor: '#fff',
                            pointBorderColor: '#1e40af'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, grid: { borderDash: [5,5] } }, x: { grid: { display: false } } }
                    }
                });

                // Agrupamos inventario por categoria
                const inventario = db.getProductos();
                const categories = {};
                inventario.forEach(p => {
                    const cat = p.categoria || 'Otros';
                    categories[cat] = (categories[cat] || 0) + 1;
                });

                const ctxP = document.getElementById('chart-pie-productos').getContext('2d');
                chartPie = new Chart(ctxP, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(categories),
                        datasets: [{
                            data: Object.values(categories),
                            backgroundColor: ['#1e40af', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                            borderWidth: 0,
                            hoverOffset: 15
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, usePointStyle: true, font: { weight: 800, size: 10 } } } },
                        cutout: '70%'
                    }
                });
            }

            // --- Exportación ---
            window.exportToExcel = function(tableId, filename) {
                const table = document.getElementById(tableId);
                const wb = XLSX.utils.table_to_book(table, { sheet: "Reporte" });
                XLSX.writeFile(wb, `${filename}_${new Date().getTime()}.xlsx`);
                Swal.fire({ icon: 'success', title: 'Excel Generado', toast: true, position: 'top-end', showConfirmButton: false, timer: 2000 });
            };

            window.exportToPDF = function(tableId, filename) {
                const { jsPDF } = window.jspdf;
                const doc = new jsPDF();
                
                doc.setFontSize(20);
                doc.setTextColor(30, 64, 175);
                doc.text("MUROTECH POS - Reporte Fiscal", 14, 22);
                
                doc.setFontSize(10);
                doc.setTextColor(100);
                doc.text(`Generado el: ${new Date().toLocaleString()}`, 14, 30);
                
                doc.autoTable({
                    html: `#${tableId}`,
                    startY: 40,
                    theme: 'striped',
                    headStyles: { fillStyle: [30, 64, 175], textColor: 255, fontStyle: 'bold' }
                });
                
                doc.save(`${filename}_${new Date().getTime()}.pdf`);
                Swal.fire({ icon: 'success', title: 'PDF Generado', toast: true, position: 'top-end', showConfirmButton: false, timer: 2000 });
            };

            // --- Carga inicial de filtros ---
            function loadFilterData() {
                const now = new Date();
                const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
                
                // Set default dates
                const desdeInput = document.getElementById('filter-desde');
                const hastaInput = document.getElementById('filter-hasta');
                
                if (desdeInput && !desdeInput.value) {
                    desdeInput.value = firstDay.toISOString().split('T')[0];
                }
                if (hastaInput && !hastaInput.value) {
                    hastaInput.value = now.toISOString().split('T')[0];
                }

                // Handler for period change
                document.getElementById('filter-periodo').addEventListener('change', function() {
                    if (this.value === 'custom') {
                        document.getElementById('range-picker').style.display = 'contents';
                    } else {
                        // In a real app, adjust dates based on period
                    }
                });
            }

            // --- Event Listeners ---
            document.getElementById('btn-filtrar').addEventListener('click', () => {
                Swal.fire({
                    title: 'Procesando Datos',
                    html: 'Generando análisis de inteligencia...',
                    timer: 800,
                    didOpen: () => Swal.showLoading()
                }).then(() => generateReport());
            });

            document.getElementById('btn-reload-data').addEventListener('click', () => {
                location.reload();
            });

            document.getElementById('btn-demo-data').addEventListener('click', () => {
                Swal.fire({
                    title: '¿Cargar datos de demostración?',
                    text: "Esto reseteará la base de datos local con información de ejemplo premium.",
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#1e40af',
                    cancelButtonColor: '#64748b',
                    confirmButtonText: 'Sí, cargar demo',
                    cancelButtonText: 'Cancelar'
                }).then((result) => {
                    if (result.isConfirmed) {
                        window.muroDB.limpiarYReiniciar();
                        location.reload();
                    }
                });
            });

            document.getElementById('btn-export-all').addEventListener('click', () => {
                Swal.fire({
                    title: '¿Generar Consolidado?',
                    text: "Se descargará un paquete completo con todos los módulos de reporte.",
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, descargar',
                    confirmButtonColor: '#1e40af'
                }).then((res) => {
                    if (res.isConfirmed) {
                        exportToExcel('table-ventas', 'Consolidado_Ventas');
                        setTimeout(() => exportToExcel('table-inventario', 'Consolidado_Inventario'), 500);
                    }
                });
            });

            // --- Inicialización ---
            loadFilterData();
            generateReport();

        })();
    


        const canvas = document.getElementById('particles-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const particles = [];
        class Particle { 
            constructor(){
                this.x=Math.random()*canvas.width;
                this.y=Math.random()*canvas.height;
                this.size=Math.random()*2+1;
                this.speedX=Math.random()*1-.5;
                this.speedY=Math.random()*1-.5;
                this.opacity=Math.random()*.4+.1;
            } 
            update(){this.x+=this.speedX;this.y+=this.speedY;if(this.x>canvas.width)this.x=0;if(this.x<0)this.x=canvas.width;if(this.y>canvas.height)this.y=0;if(this.y<0)this.y=canvas.height;} 
            draw(){ctx.fillStyle=`rgba(255,255,255,${this.opacity})`;ctx.beginPath();ctx.arc(this.x,this.y,this.size,0,Math.PI*2);ctx.fill();} 
        }
        for(let i=0;i<40;i++) particles.push(new Particle());
        function animate(){
            ctx.clearRect(0,0,canvas.width,canvas.height);
            particles.forEach(p=>{p.update();p.draw();});
            requestAnimationFrame(animate);
        }
        animate();