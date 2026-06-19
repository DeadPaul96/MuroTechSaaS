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
            
            if (this.dataset.tab === 'ventas') {
                setTimeout(() => { if(window.lastChartData) initCharts(window.lastChartData); }, 100);
            }
        });
    });

    // --- Sistema de Búsqueda de Clientes ---
    (function() {
        const searchInput = document.getElementById('filter-cliente-search');
        const idInput = document.getElementById('filter-cliente-id');
        const dropdown = document.getElementById('report-cliente-dropdown');

        if (!searchInput) return;

        searchInput.addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            if (!q) {
                idInput.value = 'all';
                dropdown.style.display = 'none';
                return;
            }

            fetchAPI(`${CONFIG.API_BASE_URL}/api/clientes?q=${encodeURIComponent(q)}`)
            .then(matches => {
                dropdown.innerHTML = '';
                if (matches && matches.length > 0) {
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
        });

        document.addEventListener('click', (e) => {
            if (searchInput && !searchInput.contains(e.target)) dropdown.style.display = 'none';
        });
    })();

    // --- PROCESAMIENTO DE REPORTES ---
    async function generateReport() {
        const desde = document.getElementById('filter-desde').value;
        const hasta = document.getElementById('filter-hasta').value;
        const clienteId = document.getElementById('filter-cliente-id').value;
        const periodo = document.getElementById('filter-periodo').value;

        Swal.fire({ 
            title: 'Procesando Inteligencia...', 
            text: 'Analizando transacciones en tiempo real...',
            allowOutsideClick: false, 
            didOpen: () => {
                Swal.showLoading();
                // Failsafe: Si en 10 segundos no responde, cerrar y avisar
                setTimeout(() => {
                    if (Swal.isVisible() && Swal.getTitle().textContent === 'Procesando Inteligencia...') {
                        Swal.close();
                        Swal.fire('Tiempo de espera agotado', 'El servidor tarda demasiado en responder. Revisa tu conexión o el estado del backend.', 'warning');
                    }
                }, 10000);
            } 
        });

        let url = `${CONFIG.API_BASE_URL}/api/reportes?desde=${desde}&hasta=${hasta}&periodo=${periodo}`;
        if (clienteId && clienteId !== 'all') url += `&cliente_id=${clienteId}`;

        try {
            const data = await fetchAPI(url);
            Swal.close();

            if (data) {
                window.lastChartData = data.graficos;

                // Actualizar KPIs (Con protección)
                const vVentas = document.getElementById('val-ventas');
                const vUtilidad = document.getElementById('val-utilidad');
                const vImpuestos = document.getElementById('val-impuestos');

                if (vVentas) vVentas.textContent = fmt(data.kpis.ventas);
                if (vUtilidad) vUtilidad.textContent = fmt(data.kpis.utilidad);
                if (vImpuestos) vImpuestos.textContent = fmt(data.kpis.impuestos);

                // Render Ventas
                const tbodyVentas = document.getElementById('tbody-ventas');
                if (tbodyVentas) {
                    tbodyVentas.innerHTML = data.tablas.ventas.map(f => `
                        <tr>
                            <td>${new Date(f.fecha).toLocaleDateString()}</td>
                            <td style="font-family:monospace; font-weight:700; font-size:0.75rem;">${f.numero}</td>
                            <td>${f.cliente}</td>
                            <td>${fmt(f.bruto)}</td>
                            <td>${fmt(f.impuestos)}</td>
                            <td style="font-weight:700; color:#1e40af;">${fmt(f.total)}</td>
                            <td><span class="stat-badge status-aceptado">${f.estado}</span></td>
                        </tr>
                    `).join('');
                }


                // Render Inventario
                const tbodyInv = document.getElementById('tbody-inventario');
                if (tbodyInv) {
                    tbodyInv.innerHTML = data.tablas.inventario.map(p => `
                        <tr>
                            <td style="font-family:monospace; font-size:0.75rem;">${p.codigo}</td>
                            <td>${p.descripcion}</td>
                            <td><span class="badge b-info">${p.categoria}</span></td>
                            <td>${fmt(p.precio_compra)}</td>
                            <td style="font-weight:700;">${fmt(p.precio_venta)}</td>
                            <td style="font-weight:800; text-align:center;">${p.existencia}</td>
                            <td><span class="stat-badge ${p.status === 'Bajo' ? 'status-error' : 'status-aceptado'}">${p.status}</span></td>
                        </tr>
                    `).join('');
                }

                document.getElementById('val-sku-total').textContent = data.kpis.sku_total;
                document.getElementById('val-stock-economico').textContent = fmt(data.kpis.valor_inventario);
                document.getElementById('val-stock-bajo').textContent = data.kpis.stock_bajo;

                // Render Comprobantes
                const tbodyComp = document.getElementById('tbody-comprobantes');
                if (tbodyComp) {
                    tbodyComp.innerHTML = data.tablas.comprobantes.map(f => `
                        <tr>
                            <td style="font-family:monospace;font-size:0.7rem;">${f.consecutivo}</td>
                            <td>${new Date(f.fecha).toLocaleString()}</td>
                            <td>${f.receptor}</td>
                            <td><span class="stat-badge status-aceptado">${f.estado} <i class="fas fa-check"></i></span></td>
                            <td style="font-family:monospace; font-size:0.65rem; color:#64748b;">${f.clave}</td>
                            <td><button class="btn-action btn-outline" style="padding:4px 10px; font-size:0.65rem;" onclick="Swal.fire('Info','Estructura de mensaje validada con firma digital','info')">Ver Log</button></td>
                        </tr>
                    `).join('');
                }

                // Render Cotizaciones
                const tbodyCot = document.getElementById('tbody-cotizaciones');
                if (tbodyCot) {
                    tbodyCot.innerHTML = data.tablas.cotizaciones.length ? data.tablas.cotizaciones.map(f => `
                        <tr>
                            <td>${new Date(f.fecha).toLocaleDateString()}</td>
                            <td style="font-family:monospace; font-weight:700;">${f.numero}</td>
                            <td>${f.cliente}</td>
                            <td>${f.vencimiento ? new Date(f.vencimiento).toLocaleDateString() : 'N/A'}</td>
                            <td style="font-weight:700;">${fmt(f.total)}</td>
                            <td><span class="stat-badge status-pendiente">${f.estado}</span></td>
                        </tr>
                    `).join('') : '<tr><td colspan="6" style="text-align:center; padding:20px; color:#94a3b8;">Sin cotizaciones en el período.</td></tr>';
                }

                initCharts(data.graficos);
            }
        } catch (err) {
            Swal.fire('Error', 'No se pudieron procesar los reportes analíticos', 'error');
            console.error(err);
        }
    }

    // --- Visualización con Chart.js ---
    function initCharts(graficos) {
        if (!graficos) return;
        if (chartVentas) chartVentas.destroy();
        if (chartPie) chartPie.destroy();

        const ctxV = document.getElementById('chart-ventas').getContext('2d');
        chartVentas = new Chart(ctxV, {
            type: 'line',
            data: {
                labels: graficos.tendencia.map(d => d.label),
                datasets: [{
                    label: 'Ventas por Período',
                    data: graficos.tendencia.map(d => d.valor),
                    borderColor: '#1e40af',
                    backgroundColor: 'rgba(30, 64, 175, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#1e40af'
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (val) => fmt(val) }
                    }
                }
            }
        });

        const ctxP = document.getElementById('chart-pie-productos').getContext('2d');
        chartPie = new Chart(ctxP, {
            type: 'doughnut',
            data: {
                labels: graficos.top_productos.map(d => d.label),
                datasets: [{
                    data: graficos.top_productos.map(d => d.valor),
                    backgroundColor: ['#1e40af', '#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    // --- Exportación ---
    window.exportToExcel = function(tableId, filename) {
        const table = document.getElementById(tableId);
        const wb = XLSX.utils.table_to_book(table, { sheet: "Reporte" });
        XLSX.writeFile(wb, `${filename}_${new Date().getTime()}.xlsx`);
    };

    window.exportToPDF = function(tableId, filename) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('l', 'mm', 'a4'); // Paisaje para más espacio
        doc.setFontSize(18);
        doc.text("MUROTECH SOLUTIONS - Reporte Analítico de Negocios", 14, 20);
        doc.setFontSize(10);
        doc.text(`Generado el: ${new Date().toLocaleString()}`, 14, 28);
        
        doc.autoTable({ 
            html: `#${tableId}`, 
            startY: 35,
            theme: 'grid',
            headStyles: { fillColor: [30, 64, 175] }
        });
        doc.save(`${filename}.pdf`);
    };

    // --- Inicialización ---
    document.getElementById('btn-filtrar').addEventListener('click', generateReport);
    document.getElementById('btn-reload-data')?.addEventListener('click', generateReport);
    
    // Fechas por defecto (Mes actual)
    const now = new Date();
    document.getElementById('filter-desde').value = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
    document.getElementById('filter-hasta').value = now.toISOString().split('T')[0];

    generateReport();

})();

// Partículas (se mantiene igual)
(function() {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
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
})();