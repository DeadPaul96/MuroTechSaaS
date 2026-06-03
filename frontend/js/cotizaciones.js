// --- LOGICA DE SIDELAR ---
if (typeof sidebarRender === 'function') sidebarRender('cotizaciones.html');

// --- DIVISAS & HACIENDA ---
let currentRates = { usd: 1, eur: 1 };
const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };

async function syncRates() {
    console.log('🔄 syncRates: Iniciando sincronización de tasas...');
    const status = document.getElementById('dash-tc-status');
    
    try {
        if (status) {
            status.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> CONECTANDO...';
            status.style.background = '#e2e8f0';
            status.style.color = '#0f172a';
        }

        console.log('🌐 Llamando a API tipo-cambio...');
        const data = await fetchAPI(`${CONFIG.API_BASE_URL}/api/tipo-cambio`);
        console.log('✅ Respuesta de API tipo-cambio:', data);
        
        if (!data || !data.venta || !data.euro_colones) {
            console.error('❌ Respuesta inválida:', data);
            throw new Error('Respuesta inválida de tipo de cambio');
        }

        currentRates = { usd: data.venta, eur: data.euro_colones };
        const fmtRate = (val) => '₡' + Number(val).toLocaleString('es-CR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

        const elUsdVenta = document.getElementById('fx-usd-venta');
        const elEurValor = document.getElementById('fx-eur-valor');
        const elUsdFecha = document.getElementById('fx-usd-fecha');
        const elEurFecha = document.getElementById('fx-eur-fecha');

        if (elUsdVenta) elUsdVenta.textContent = fmtRate(currentRates.usd);
        if (elEurValor) elEurValor.textContent = fmtRate(currentRates.eur);
        if (elUsdFecha) elUsdFecha.textContent = new Date().toLocaleDateString('es-CR');
        if (elEurFecha) elEurFecha.textContent = new Date().toLocaleDateString('es-CR');

        if (status) {
            status.innerHTML = `<i class="fas fa-check-circle"></i> SINCRONIZADO`;
            status.style.background = '#ecfdf5';
            status.style.color = '#10b981';
        }
        
        console.log('✅ syncRates: Completado exitosamente');
    } catch (err) {
        console.error('❌ syncRates Error:', err);
        const elUsdVenta = document.getElementById('fx-usd-venta');
        const elEurValor = document.getElementById('fx-eur-valor');
        if (elUsdVenta) elUsdVenta.textContent = 'No disponible';
        if (elEurValor) elEurValor.textContent = 'No disponible';

        if (status) {
            status.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ERROR API';
            status.style.background = '#fef2f2';
            status.style.color = '#ef4444';
        }
    }
}

async function syncTime() {
    console.log('⏰ syncTime: Iniciando sincronización de reloj...');
    const timeEl = document.getElementById('realtime-date');
    const statusEl = document.getElementById('realtime-status');
    const dot = document.getElementById('clock-dot');
    
    if (!timeEl) {
        console.error('❌ No se encontró el elemento realtime-date');
        return;
    }

    if (statusEl) {
        statusEl.innerText = `CONECTANDO...`;
        statusEl.style.color = '#2563eb';
        statusEl.style.background = '#eff6ff';
    }

    // Actualizar reloj cada segundo
    setInterval(() => {
        const now = new Date();
        const dateStr = now.toLocaleDateString('es-CR', { day:'2-digit', month:'2-digit', year:'numeric' });
        const timeStr = now.toLocaleTimeString('es-CR', { hour:'2-digit', minute:'2-digit', hour12: true });
        timeEl.innerText = `${dateStr} — ${timeStr.toLowerCase()}`;
    }, 1000);

    // Sincronizar con API
    try {
        console.log('🌐 Llamando a API /api/time...');
        const res = await fetchAPI(`${CONFIG.API_BASE_URL}/api/time`);
        console.log('✅ Respuesta de API time:', res);
        
        if (res && res.datetime && statusEl) {
            statusEl.innerHTML = `SINCRONIZADO`;
            statusEl.style.color = '#10b981';
            statusEl.style.background = 'transparent';
            if (dot) dot.style.background = '#10b981';
        }
        console.log('✅ syncTime: Completado exitosamente');
    } catch (e) {
        console.warn('⚠️ Error syncTime, usando respaldo local:', e);
        if (statusEl) {
            statusEl.innerHTML = `SINCRONIZADO`;
            statusEl.style.color = '#10b981';
            statusEl.style.background = 'transparent';
        }
        if (dot) dot.style.background = '#10b981';
    }
}

function updateVencimiento() {
    const dias = parseInt(document.getElementById('validez-dias').value, 10) || 15;
    const fecha = new Date();
    fecha.setDate(fecha.getDate() + dias);
    const iso = fecha.toISOString().slice(0, 10);
    const fechaInput = document.getElementById('fecha-vencimiento');
    if (fechaInput) fechaInput.value = iso;
}

function formatCurrency(value, symbol) {
    return symbol + Number(value).toLocaleString('es-CR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function buildQuotationPdf() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const fechaHoy = new Date().toLocaleDateString('es-CR');
    const moneda = document.getElementById('moneda')?.value || 'CRC';
    const symbol = monedaSymbols[moneda] || '₡';
    const clienteData = getClienteData();
    const notas = document.getElementById('notas-cotizacion')?.value || '';

    doc.setFontSize(20);
    doc.setFont(undefined, 'bold');
    doc.text('PROFORMA / COTIZACIÓN', 14, 18);
    doc.setFontSize(10);
    doc.setFont(undefined, 'normal');
    doc.text('MUROTECH SOLUTIONS S.A.', 14, 28);
    doc.text('Cédula Jurídica: 3-101-897564', 14, 34);
    doc.text(`Fecha: ${fechaHoy}`, 160, 28, { align: 'right' });
    doc.text(`Moneda: ${moneda}`, 160, 34, { align: 'right' });

    doc.setDrawColor(220, 220, 220);
    doc.line(14, 50, 196, 50);

    doc.setFontSize(12);
    doc.setFont(undefined, 'bold');
    doc.text('Cliente / Prospecto', 14, 58);
    doc.setFont(undefined, 'normal');
    doc.text(clienteData.nombre, 14, 64);
    doc.text(`Cédula: ${clienteData.cedula}`, 14, 70);

    const items = Array.from(document.querySelectorAll('.item-card')).map(card => {
        return {
            cantidad: card.querySelector('.item-qty')?.value || '0',
            descripcion: card.querySelector('.item-detail')?.value || card.querySelector('h4')?.textContent || 'Descripción',
            precio: Number(card.dataset.precioOriginal || 0).toFixed(2),
            descuento: Number(card.querySelector('.item-desc-pct')?.value || 0).toFixed(2),
            total: (Number(card.querySelector('.item-qty')?.value || 0) * Number(card.dataset.precioOriginal || 0) * (1 - Number(card.querySelector('.item-desc-pct')?.value || 0) / 100)).toFixed(2)
        };
    });

    const body = items.map(item => [
        item.cantidad,
        item.descripcion,
        `${symbol}${Number(item.precio).toLocaleString('es-CR', {minimumFractionDigits:2})}`,
        `${item.descuento}%`,
        `${symbol}${Number(item.total).toLocaleString('es-CR', {minimumFractionDigits:2})}`
    ]);

    doc.autoTable({
        startY: 82,
        head: [['Cant.', 'Descripción', 'P. Unit.', 'Desc.', 'Total']],
        body,
        headStyles: { fillColor: '#1e40af', textColor: '#ffffff' },
        styles: { fontSize: 9 }
    });

    const finalY = doc.lastAutoTable.finalY + 10;
    doc.setFontSize(10);
    doc.text(`Subtotal: ${document.getElementById('total-subtotal')?.textContent || symbol + '0.00'}`, 140, finalY);
    doc.text(`Descuentos: ${document.getElementById('total-descuento')?.textContent || symbol + '0.00'}`, 140, finalY + 6);
    doc.text(`IVA Estimado: ${document.getElementById('total-impuesto')?.textContent || symbol + '0.00'}`, 140, finalY + 12);
    doc.setFont(undefined, 'bold');
    doc.setFontSize(12);
    doc.text(`TOTAL: ${document.getElementById('total-final')?.textContent || symbol + '0.00'}`, 140, finalY + 22);

    if (notas) {
        doc.setFont(undefined, 'normal');
        doc.setFontSize(10);
        doc.text('Notas:', 14, finalY);
        doc.setFontSize(9);
        doc.text(notas, 14, finalY + 6, { maxWidth: 120 });
    }

    return doc;
}

function downloadQuotationPDF() {
    const doc = buildQuotationPdf();
    doc.save(`MUROTECH_Cotizacion_${new Date().toISOString().slice(0,10)}.pdf`);
}

document.getElementById('btn-download-pdf')?.addEventListener('click', () => {
    downloadQuotationPDF();
});

document.getElementById('validez-dias')?.addEventListener('input', updateVencimiento);

// Inicializar sincronización
syncRates();
syncTime();
setInterval(syncRates, 30000); // Sincronizar tasas cada 30 segundos
updateVencimiento();

/* ======= MOTOR DE CLIENTES (MANUAL) ======= */
// Los datos del cliente se capturan directamente de los inputs
window.getClienteData = function() {
    return {
        nombre: document.getElementById('prospecto-nombre')?.value || 'Cliente no especificado',
        cedula: document.getElementById('prospecto-cedula')?.value || '---'
    };
};

// --- PRODUCTOS ---
(function() {
    const input = document.getElementById('buscar-cabys');
    const dropdown = document.getElementById('cabys-dropdown');
    const token = localStorage.getItem('token');
    if (!input || !dropdown) return;

    function closeDropdown() { dropdown.style.display = 'none'; dropdown.innerHTML = ''; }

    input.addEventListener('input', async function() {
        const q = this.value.trim().toLowerCase();
        if (q.length < 1) { closeDropdown(); return; }

        try {
            const matches = await fetchAPI(`${CONFIG.API_BASE_URL}/api/productos?q=${encodeURIComponent(q)}`);
            dropdown.innerHTML = '';
            if (!matches || !matches.length) {
                dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">Sin resultados</div>';
            } else {
                const filtered = matches.filter(p =>
                    (p.nombre || p.descripcion || '').toLowerCase().includes(q) ||
                    (p.cabys || '').toLowerCase().includes(q) ||
                    (p.codigo || '').toLowerCase().includes(q) ||
                    (p.marca || '').toLowerCase().includes(q) ||
                    (p.modelo || '').toLowerCase().includes(q)
                );

                if (filtered.length === 0) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No hay coincidencias exactas</div>';
                } else {
                    filtered.slice(0, 10).forEach(prod => {
                        const identity = [prod.marca, prod.modelo, prod.caracteristicas].filter(Boolean).join(' ');
                        const title = identity || prod.nombre || prod.descripcion || 'Producto';
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.style.display = 'flex';
                        item.style.justifyContent = 'space-between';
                        item.style.alignItems = 'center';
                        item.innerHTML = `
                            <div style="flex:1;">
                                <div style="font-weight:900; color:#0f172a;">${title}</div>
                                <div style="font-size:0.65rem; color:#94a3b8;">${prod.cabys || '—'}</div>
                            </div>
                            <div style="font-weight:900; color:#1e40af; white-space:nowrap; margin-left:12px;">₡${(prod.precioVenta || prod.precio || 0).toLocaleString('es-CR', {minimumFractionDigits:2})}</div>
                        `;
                        item.onclick = () => {
                            input.value = '';
                            closeDropdown();
                            agregarLineaProducto(prod);
                        };
                        dropdown.appendChild(item);
                    });
                }
            }
            dropdown.style.display = 'block';
        } catch (err) {
            console.error('Error al buscar productos:', err);
            dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#ef4444; font-size:0.8rem;">Error al consultar productos</div>';
            dropdown.style.display = 'block';
        }
    });

    document.addEventListener('click', function(event) {
        if (event.target !== input) closeDropdown();
    });
})();

window.agregarLineaProducto = function(prod = null) {
    const empty = document.getElementById('empty-row');
    if (empty) empty.remove();

    const detailLinesContainer = document.getElementById('detalle-lineas');
    const lineIndex = detailLinesContainer.querySelectorAll('.item-card').length + 1;
    const symbol = monedaSymbols[document.getElementById('moneda')?.value] || '₡';

    let displayDetail = 'Ítem manual';
    let precioRef = 0;
    let cabys = '0000';
    let codigo = 'N/A';
    let impuesto = 13;
    let descMax = 0;

    if (prod) {
        displayDetail = [prod.marca, prod.modelo, prod.caracteristicas].filter(Boolean).join(' ').trim() || prod.nombre || prod.descripcion || 'Producto';
        precioRef = prod.precioVenta || prod.precio || 0;
        cabys = prod.cabys || '0000';
        codigo = prod.codigo || prod.sku || 'N/A';
        impuesto = prod.impuesto || 13;
        descMax = prod.descuentoMax || 0;
    }

    const card = document.createElement('div');
    card.id = 'linea-' + Date.now();
    card.className = 'item-card fac-line-item';
    card.dataset.precioOriginal = precioRef;
    card.dataset.productoId = prod?.id || '';
    card.dataset.descMax = descMax;

    card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="background:#2563eb; color:white; width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:900;">#${lineIndex}</div>
                <h4 style="margin:0; font-size:1.1rem; font-weight:950; color:#0f172a; letter-spacing:-0.5px;">${displayDetail}</h4>
            </div>
            <div style="display:flex; gap:8px;">
                <button type="button" onclick="configurarExoneracion('${card.id}')" style="background:#fff7ed; border:1.5px solid #fbbf24; color:#9a3412; padding:4px 12px; border-radius:8px; font-size:0.7rem; font-weight:900; cursor:pointer;"><i class="fas fa-shield-alt"></i> EXO</button>
                <button type="button" onclick="eliminarLinea('${card.id}')" style="background:#fff1f2; border:1.5px solid #fecdd3; color:#ef4444; width:32px; height:32px; border-radius:8px; cursor:pointer;"><i class="fas fa-trash-alt"></i></button>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:flex-end; gap:20px;">
            <div style="display:flex; gap:10px; flex-shrink:0;">
                <div>
                    <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">SKU</label>
                    <div style="background:white; height:32px; padding:0 12px; border-radius:10px; border:1.5px solid #e2e8f0; font-size:0.8rem; font-weight:800; color:#475569; font-family:var(--font-mono); display:flex; align-items:center; justify-content:center; min-width:80px;">${codigo}</div>
                </div>
                <div>
                    <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">CABYS</label>
                    <div style="background:white; height:32px; padding:0 12px; border-radius:10px; border:1.5px solid #e2e8f0; font-size:0.8rem; font-weight:800; color:#475569; font-family:var(--font-mono); display:flex; align-items:center; justify-content:center; min-width:110px;">${cabys}</div>
                </div>
            </div>
            <div style="display:flex; gap:10px; flex:1; justify-content:center;">
                <div style="width:65px;">
                    <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">CANT.</label>
                    <input type="number" class="item-qty fi" value="1" min="1" oninput="recalcularTotales()" style="width:100%; height:32px; text-align:center; font-weight:950; font-size:0.95rem; border-radius:10px; padding:0; border:1.5px solid #e2e8f0;">
                </div>
                <div style="width:85px;">
                    <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">DESC. %</label>
                    <div style="position:relative;">
                        <input type="number" class="item-desc-pct fi" value="0" min="0" oninput="recalcularTotales()" style="width:100%; height:32px; text-align:center; font-weight:950; font-size:0.95rem; color:#ef4444; background:#fff1f2; border:1.5px solid #fecdd3; border-radius:10px; padding-right:15px;">
                        <span style="position:absolute; right:6px; top:50%; transform:translateY(-50%); font-weight:900; color:#ef4444; font-size:0.75rem;">%</span>
                    </div>
                </div>
                <div style="width:85px;">
                    <label style="display:block; font-size:0.55rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:4px; text-align:center;">IVA %</label>
                    <div style="position:relative;">
                        <input type="number" class="item-tax-pct fi" value="${impuesto}" readonly style="width:100%; height:32px; text-align:center; font-weight:950; font-size:0.95rem; color:#059669; background:#ecfdf5; border:1.5px solid #d1fae5; border-radius:10px; padding-right:15px;">
                        <span style="position:absolute; right:6px; top:50%; transform:translateY(-50%); font-weight:900; color:#059669; font-size:0.75rem;">%</span>
                    </div>
                </div>
            </div>
            <div style="text-align:right; flex-shrink:0;">
                <label style="display:block; font-size:0.6rem; font-weight:900; color:#94a3b8; text-transform:uppercase; margin-bottom:2px;">SUBTOTAL ÍTEM</label>
                <input type="hidden" class="item-detail" value="${displayDetail}">
                <span class="subtotal-cell" style="font-weight:950; color:#1e40af; font-size:1.8rem; letter-spacing:-1px; line-height:1;">${symbol}0,00</span>
            </div>
        </div>
    `;

    detailLinesContainer.appendChild(card);
    recalcularTotales();
};

window.eliminarLinea = function(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const detailLinesContainer = document.getElementById('detalle-lineas');
    el.remove();
    if (detailLinesContainer.querySelectorAll('.item-card').length === 0) {
        detailLinesContainer.innerHTML = `
            <div id="empty-row" style="text-align:center; padding:50px 20px; color:#94a3b8; background: #fff; border: 2px dashed #e2e8f0; border-radius: 16px;">
                <i class="fas fa-box-open" style="display:block; font-size:2.5rem; margin-bottom:12px; opacity:0.2;"></i>
                <div style="font-weight: 800; font-size: 1rem; color: #64748b;">No hay productos en la lista</div>
                <p style="font-size: 0.75rem; margin-top: 4px;">Usa el buscador superior para agregar servicios o productos</p>
            </div>
        `;
    }
    recalcularTotales();
};

window.configurarExoneracion = function(id) {
    const card = document.getElementById(id);
    if (!card) return;
    Swal.fire('Exoneración', 'Configuración de exoneración no disponible en cotización.', 'info');
};

window.recalcularTotales = function() {
    let subtotalTotal = 0;
    let descTotal = 0;
    let taxTotal = 0;
    const symbol = monedaSymbols[document.getElementById('moneda')?.value] || '₡';
    document.querySelectorAll('.item-card').forEach(card => {
        const precio = parseFloat(card.dataset.precioOriginal) || 0;
        const cant = parseFloat(card.querySelector('.item-qty')?.value) || 0;
        const descPct = parseFloat(card.querySelector('.item-desc-pct')?.value) || 0;
        const taxPct = parseFloat(card.querySelector('.item-tax-pct')?.value) || 0;
        const base = precio * cant;
        const desc = base * (descPct / 100);
        const neto = base - desc;
        const tax = neto * (taxPct / 100);
        const lineaTotal = neto + tax;
        card.querySelector('.subtotal-cell').textContent = symbol + lineaTotal.toLocaleString('es-CR', {minimumFractionDigits:2});
        subtotalTotal += base;
        descTotal += desc;
        taxTotal += tax;
    });
    const final = subtotalTotal - descTotal + taxTotal;
    const fmt = (v) => symbol + v.toLocaleString('es-CR', {minimumFractionDigits:2});
    document.getElementById('total-subtotal').textContent = fmt(subtotalTotal);
    document.getElementById('total-descuento').textContent = fmt(descTotal);
    document.getElementById('total-impuesto').textContent = fmt(taxTotal);
    document.getElementById('total-final').textContent = fmt(final);
};

// --- SUBMIT ---
document.getElementById('proforma-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const clienteData = getClienteData();
    const moneda = document.getElementById('moneda').value;
    const notas = document.getElementById('notas-cotizacion')?.value || '';
    const vencimiento = document.getElementById('fecha-vencimiento')?.value || '';

    if (!clienteData.nombre.trim()) {
        Swal.fire('Error', 'Por favor ingresa el nombre del cliente', 'error');
        return;
    }

    const items = [];
    document.querySelectorAll('.item-card').forEach(card => {
        items.push({
            producto_id: card.dataset.productoId || null,
            cantidad: card.querySelector('.item-qty')?.value || 0,
            descripcion: card.querySelector('.item-detail')?.value || card.querySelector('h4')?.textContent || 'Ítem',
            precio_unitario: card.dataset.precioOriginal || 0,
            descuento: card.querySelector('.item-desc-pct')?.value || 0,
            impuesto: card.querySelector('.item-tax-pct')?.value || 0
        });
    });

    if (items.length === 0) {
        Swal.fire('Error', 'Agrega al menos un producto a la cotización', 'error');
        return;
    }

    const token = localStorage.getItem('token');
    try {
        const res = await fetch(`${CONFIG.API_BASE_URL}/api/cotizaciones`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                cliente_nombre: clienteData.nombre,
                cliente_cedula: clienteData.cedula,
                moneda: moneda,
                notas: notas,
                vencimiento: vencimiento,
                items: items,
                total: parseFloat(document.getElementById('total-final').textContent.replace(/[^\d.-]/g, ''))
            })
        });

        if (res.ok) {
            const data = await res.json();
            const doc = buildQuotationPdf();
            doc.save(`MUROTECH_Cotizacion_${data.id || new Date().toISOString().slice(0,10)}.pdf`);
            Swal.fire('¡Éxito!', 'Cotización guardada y PDF descargado.', 'success').then(() => {
                window.location.reload();
            });
        } else {
            Swal.fire('Error', 'No se pudo guardar la cotización', 'error');
        }
    } catch (err) {
        console.error(err);
        Swal.fire('Error', 'Error al guardar la cotización', 'error');
    }
});

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