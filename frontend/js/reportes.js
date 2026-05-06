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

            const token = localStorage.getItem('token');
            fetch(`${CONFIG.API_BASE_URL}/api/clientes?q=${encodeURIComponent(q)}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.json())
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
        const token = localStorage.getItem('token');
        if (!token) return;

        const desde = document.getElementById('filter-desde').value;
        const hasta = document.getElementById('filter-hasta').value;
        const clienteId = document.getElementById('filter-cliente-id').value;

        let url = `${CONFIG.API_BASE_URL}/api/reportes/data?desde=${desde}&hasta=${hasta}`;
        if (clienteId && clienteId !== 'all') url += `&cliente_id=${clienteId}`;

        try {
            const res = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();

            if (res.ok) {
                window.lastChartData = data.charts;

                // Actualizar KPIs
                document.getElementById('val-ventas').textContent = fmt(data.kpis.ventas);
                document.getElementById('val-compras').textContent = fmt(data.kpis.compras);
                document.getElementById('val-utilidad').textContent = fmt(data.kpis.utilidad);
                document.getElementById('val-impuestos').textContent = fmt(data.kpis.iva);

                // Render Ventas
                const tbodyVentas = document.getElementById('tbody-ventas');
                if (tbodyVentas) {
                    tbodyVentas.innerHTML = data.tablas.ventas.map(f => `
                        <tr>
                            <td>${f.fecha}</td>
                            <td style="font-family:monospace; font-weight:700; font-size:0.75rem;">${f.consecutivo}</td>
                            <td>${f.cliente}</td>
                            <td>${fmt(f.bruto)}</td>
                            <td>${fmt(f.iva)}</td>
                            <td style="font-weight:700; color:var(--rep-accent);">${fmt(f.total)}</td>
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
                            <td>${p.nombre}</td>
                            <td><span class="badge b-info">General</span></td>
                            <td>${fmt(p.costo)}</td>
                            <td style="font-weight:700;">${fmt(p.venta)}</td>
                            <td style="font-weight:800; text-align:center;">${p.stock}</td>
                            <td><span class="stat-badge ${p.status === 'STOCK_BAJO' ? 'status-error' : 'status-aceptado'}">${p.status}</span></td>
                        </tr>
                    `).join('');
                }

                document.getElementById('val-sku-total').textContent = data.resumen_inventario.total_skus;
                document.getElementById('val-stock-economico').textContent = fmt(data.resumen_inventario.valor_total);
                document.getElementById('val-stock-bajo').textContent = data.resumen_inventario.conteo_bajo;

                // Render Comprobantes
                const tbodyComp = document.getElementById('tbody-comprobantes');
                if (tbodyComp) {
                    tbodyComp.innerHTML = data.tablas.ventas.map(f => `
                        <tr>
                            <td style="font-family:monospace;font-size:0.7rem;">${f.consecutivo}</td>
                            <td>${f.fecha}</td>
                            <td>${f.cliente}</td>
                            <td><span class="stat-badge status-aceptado">${f.estado} <i class="fas fa-check"></i></span></td>
                            <td style="font-family:monospace; font-size:0.65rem; color:#64748b;">Clave Generada</td>
                            <td><button class="btn-action btn-outline" style="padding:4px 10px; font-size:0.65rem;">Ver XML</button></td>
                        </tr>
                    `).join('');
                }

                initCharts(data.charts);
            }
        } catch (err) {
            console.error("Error al cargar reportes:", err);
        }
    }

    // --- Visualización con Chart.js ---
    function initCharts(charts) {
        if (!charts) return;
        if (chartVentas) chartVentas.destroy();
        if (chartPie) chartPie.destroy();

        const ctxV = document.getElementById('chart-ventas').getContext('2d');
        chartVentas = new Chart(ctxV, {
            type: 'line',
            data: {
                labels: charts.ventas.map(d => d.fecha),
                datasets: [{
                    label: 'Ventas Diarias',
                    data: charts.ventas.map(d => d.total),
                    borderColor: '#1e40af',
                    backgroundColor: 'rgba(30, 64, 175, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        const ctxP = document.getElementById('chart-pie-productos').getContext('2d');
        chartPie = new Chart(ctxP, {
            type: 'doughnut',
            data: {
                labels: charts.productos.map(d => d.label),
                datasets: [{
                    data: charts.productos.map(d => d.value),
                    backgroundColor: ['#1e40af', '#3b82f6', '#10b981', '#f59e0b', '#ef4444']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
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
        const doc = new jsPDF();
        doc.text("MUROTECH - Reporte Fiscal", 14, 20);
        doc.autoTable({ html: `#${tableId}`, startY: 30 });
        doc.save(`${filename}.pdf`);
    };

    // --- Inicialización ---
    document.getElementById('btn-filtrar').addEventListener('click', generateReport);
    
    // Fechas por defecto
    const now = new Date();
    document.getElementById('filter-desde').value = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
    document.getElementById('filter-hasta').value = now.toISOString().split('T')[0];

    generateReport();

})();

// Partículas
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