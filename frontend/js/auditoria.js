(function(){
    let activeTab = 'comprobantes';

    async function init() {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        document.getElementById('aud-desde').value = firstDay.toISOString().split('T')[0];
        document.getElementById('aud-hasta').value = now.toISOString().split('T')[0];

        setupTabs();
        setupFilters();
        await cargarVendedores();
        await render();
    }

    async function cargarVendedores() {
        try {
            const users = await fetchAPI(`${CONFIG.API_BASE_URL}/api/usuarios`);
            const select = document.getElementById('aud-vendedor');
            if (select && users) {
                users.forEach(u => {
                    const opt = document.createElement('option');
                    opt.value = u.id;
                    opt.textContent = u.nombre;
                    select.appendChild(opt);
                });
            }
        } catch (err) {
            console.error("Error cargando vendedores:", err);
        }
    }

    function setupTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.onclick = async function() {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
                this.classList.add('active');
                activeTab = this.dataset.tab;
                document.getElementById('panel-' + activeTab).classList.add('active');
                await render();
            };
        });
    }

    function setupFilters() {
        document.getElementById('btn-do-filter').onclick = () => render();
    }

    function fmt(n) { return new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', minimumFractionDigits: 0 }).format(n || 0); }

    async function render() {
        const desde = document.getElementById('aud-desde').value;
        const hasta = document.getElementById('aud-hasta').value;
        const estado = document.getElementById('aud-estado').value;
        const vendedor = document.getElementById('aud-vendedor').value;
        const pago = document.getElementById('aud-pago').value;
        const q = document.getElementById('aud-search').value;

        Swal.fire({ title: 'Analizando...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

        try {
            const url = `${CONFIG.API_BASE_URL}/api/auditoria?desde=${desde}&hasta=${hasta}&estado=${estado}&vendedor_id=${vendedor}&medio_pago=${pago}&q=${encodeURIComponent(q)}`;
            const res = await fetchAPI(url);
            Swal.close();

            if (!res) return;

            // 1. Comprobantes
            const listMh = document.getElementById('list-mh');
            if (listMh) {
                listMh.innerHTML = res.comprobantes.map(f => {
                    const date = new Date(f.fecha);
                    return `
                        <tr>
                            <td>
                                <div style="font-weight:800;">${date.toLocaleDateString()}</div>
                                <div style="font-size:0.7rem; color:#64748b;">${date.toLocaleTimeString()}</div>
                            </td>
                            <td>
                                <div style="font-family:monospace; font-weight:800; font-size:0.85rem;">${f.consecutivo}</div>
                                <div style="font-family:monospace; font-size:0.65rem; color:#94a3b8;">${f.clave}</div>
                            </td>
                            <td>
                                <div style="font-weight:700;">${f.receptor}</div>
                                <div style="font-size:0.7rem; color:#64748b;"><i class="fas fa-user-tag"></i> ${f.vendedor}</div>
                            </td>
                            <td style="font-weight:900; color:#1e40af;">
                                ${fmt(f.monto)}
                                <div style="font-size:0.65rem; font-weight:700; color:#64748b;">${f.medio_pago}</div>
                            </td>
                            <td><span class="badge b-success"><i class="fas fa-check-circle"></i> ${f.estado.toUpperCase()}</span></td>
                            <td style="text-align:center; display:flex; gap:5px; justify-content:center;">
                                <button class="btn-circle ${f.has_pdf ? 'yellow-btn' : 'disabled-btn'}" title="Descargar PDF" onclick="descargarArchivo(${f.id}, 'pdf')">
                                    <i class="fas fa-file-pdf"></i>
                                </button>
                                <button class="btn-circle ${f.has_xml ? 'yellow-btn' : 'disabled-btn'}" title="Descargar XML" onclick="descargarArchivo(${f.id}, 'xml')">
                                    <i class="fas fa-code"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            // 2. Movimientos
            const listInv = document.getElementById('list-inv');
            if (listInv) {
                listInv.innerHTML = res.movimientos.map(m => `
                    <tr>
                        <td>${new Date(m.fecha).toLocaleDateString()}</td>
                        <td style="font-weight:800;">${m.producto}</td>
                        <td><span class="badge ${m.tipo === 'Venta' ? 'b-success' : 'b-warning'}">${m.tipo}</span></td>
                        <td>${m.anterior}</td>
                        <td style="color:${m.ajuste < 0 ? '#dc2626' : '#16a34a'}; font-weight:800;">${m.ajuste > 0 ? '+' : ''}${m.ajuste}</td>
                        <td style="font-weight:900;">${m.actual}</td>
                        <td style="font-weight:700; font-size:0.75rem;">${m.usuario}</td>
                    </tr>
                `).join('');
            }

            // 3. Bitácora Ventas
            const listSales = document.getElementById('list-sales');
            if (listSales) {
                listSales.innerHTML = res.ventas.map(v => `
                    <tr>
                        <td>${new Date(v.fecha).toLocaleDateString()}</td>
                        <td style="font-family:monospace; font-weight:800;">${v.transaccion}</td>
                        <td>${v.caja}</td>
                        <td>${v.vendedor}</td>
                        <td style="font-weight:900;">${fmt(v.monto)}</td>
                        <td><span class="badge b-info">${v.medio_pago}</span></td>
                        <td style="text-align:center;"><button class="btn-circle" onclick="Swal.fire('Info','Transacción procesada correctamente','info')"><i class="fas fa-search-plus"></i></button></td>
                    </tr>
                `).join('');
            }

        } catch (err) {
            Swal.fire('Error', 'No se pudieron cargar los datos de auditoría', 'error');
        }
    }

    window.descargarArchivo = async function(id, tipo) {
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`${CONFIG.API_BASE_URL}/api/facturas/descargar/${id}/${tipo}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!res.ok) throw new Error('Archivo no disponible');

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Documento_${id}.${tipo === 'xml' ? 'xml' : 'pdf'}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err) {
            Swal.fire('Error', err.message, 'error');
        }
    };

    init();
})();