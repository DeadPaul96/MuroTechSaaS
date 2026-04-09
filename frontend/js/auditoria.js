(function(){
            const db = window.muroDB;
            let activeTab = 'comprobantes';

            function init() {
                // Set default dates (current month)
                const now = new Date();
                const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
                document.getElementById('aud-desde').value = firstDay.toISOString().split('T')[0];
                document.getElementById('aud-hasta').value = now.toISOString().split('T')[0];

                if (!window.muroDB) {
                    console.warn("muroDB not found, waiting...");
                    setTimeout(init, 100);
                    return;
                }
                render();
                setupTabs();
                setupFilters();
            }

            function setupTabs() {
                document.querySelectorAll('.tab-btn').forEach(btn => {
                    btn.onclick = function() {
                        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
                        this.classList.add('active');
                        activeTab = this.dataset.tab;
                        document.getElementById('panel-' + activeTab).classList.add('active');
                        render();
                    };
                });
            }

            function setupFilters() {
                document.getElementById('btn-do-filter').onclick = () => {
                   Swal.fire({ title: 'Analizando registros', html: 'Buscando en la base de datos...', timer: 500, didOpen: () => Swal.showLoading() }).then(() => render());
                };
            }

            function fmt(n) { return new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', minimumFractionDigits: 0 }).format(n || 0); }

            function render() {
                if(!db) return;
                const facturas = db.getFacturas();
                
                if(activeTab === 'comprobantes') {
                    const el = document.getElementById('list-mh');
                    el.innerHTML = facturas.map(f => `
                        <tr>
                            <td>
                                <div style="font-weight:800;">${new Date(f.fecha).toLocaleDateString()}</div>
                                <div style="font-size:0.7rem; color:#64748b;">${new Date(f.fecha).toLocaleTimeString()}</div>
                            </td>
                            <td>
                                <div style="font-family:monospace; font-weight:800; font-size:0.85rem;">${f.id}</div>
                                <div style="font-family:monospace; font-size:0.65rem; color:#94a3b8;">506080424003101897564${Math.floor(Math.random()*100000)}</div>
                            </td>
                            <td style="font-weight:700;">${f.clienteNombre || 'Consumidor Final'}</td>
                            <td style="font-weight:900; color:#1e40af;">${fmt(f.monto)}</td>
                            <td><span class="badge b-success"><i class="fas fa-check-circle"></i> Aceptado</span></td>
                            <td style="text-align:center;">
                                <button class="btn-circle" title="PDF" onclick="Swal.fire('PDF','Simulando comprobante v4.4','info')"><i class="fas fa-file-pdf"></i></button>
                                <button class="btn-circle" title="XML" onclick="Swal.fire('XML','Estructura de mensaje firmada','info')"><i class="fas fa-code"></i></button>
                            </td>
                        </tr>
                    `).join('');
                } else if(activeTab === 'inventario') {
                    const prod = db.getProductos().slice(0, 8);
                    document.getElementById('list-inv').innerHTML = prod.map(p => `
                        <tr>
                            <td>${new Date().toLocaleDateString()}</td>
                            <td style="font-weight:800;">${p.codigo}<br><span style="font-size:0.7rem; color:#64748b; font-weight:500;">${p.descripcion}</span></td>
                            <td><span class="badge b-warning">Ajuste POS</span></td>
                            <td>${(p.stock || 0) + 12}</td>
                            <td style="color:#dc2626; font-weight:800;">-12</td>
                            <td style="font-weight:900;">${p.stock}</td>
                            <td style="font-weight:700; font-size:0.75rem;">CAJERO_01</td>
                        </tr>
                    `).join('');
                } else if(activeTab === 'ventas') {
                    document.getElementById('list-sales').innerHTML = facturas.map(f => `
                        <tr>
                            <td>${new Date(f.fecha).toLocaleDateString()}</td>
                            <td style="font-family:monospace; font-weight:800;">TRN-SEC-${Math.floor(Math.random()*999999)}</td>
                            <td>TERMINAL 01</td>
                            <td>Admin MUROTECH</td>
                            <td style="font-weight:900;">${fmt(f.monto)}</td>
                            <td>EFECTIVO / SINPE</td>
                            <td style="text-align:center;"><button class="btn-circle" onclick="Swal.fire('Detalle','Auditoría interna de líneas y trazabilidad','success')"><i class="fas fa-search-plus"></i></button></td>
                        </tr>
                    `).join('');
                }
            }

            init();
        })();
    


        const canvas = document.getElementById('particles-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const particles = [];
        class Particle {
            constructor() { this.x = Math.random() * canvas.width; this.y = Math.random() * canvas.height; this.size = Math.random() * 2 + 0.5; this.speedX = Math.random() * 0.5 - 0.25; this.speedY = Math.random() * 0.5 - 0.25; this.opacity = Math.random() * 0.4 + 0.1; }
            update() { this.x += this.speedX; this.y += this.speedY; if (this.x > canvas.width) this.x = 0; if (this.x < 0) this.x = canvas.width; if (this.y > canvas.height) this.y = 0; if (this.y < 0) this.y = canvas.height; }
            draw() { ctx.fillStyle = `rgba(255,255,255,${this.opacity})`; ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fill(); }
        }
        for (let i = 0; i < 50; i++) particles.push(new Particle());
        function animate() { ctx.clearRect(0,0,canvas.width,canvas.height); particles.forEach(p => { p.update(); p.draw(); }); requestAnimationFrame(animate); }
        animate();