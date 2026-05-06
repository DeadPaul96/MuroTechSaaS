// --- LOGICA DE SIDELAR ---
if (typeof sidebarRender === 'function') sidebarRender('cotizaciones.html');

// --- DIVISAS & HACIENDA ---
let currentRates = { usd: 1, eur: 1 };
const monedaSymbols = { 'CRC': '₡', 'USD': '$', 'EUR': '€' };

async function syncRates() {
    try {
        const res = await fetch("https://api.hacienda.go.cr/indicadores/tc");
        if (res.ok) {
            const data = await res.json();
            if (data.dolar) {
                currentRates.usd = data.dolar.venta.valor;
                document.getElementById('fx-usd-venta').textContent = '₡' + currentRates.usd.toFixed(2);
            }
            if (data.euro) {
                currentRates.eur = data.euro.colones;
                document.getElementById('fx-eur-valor').textContent = '₡' + currentRates.eur.toFixed(2);
            }
        }
    } catch (e) { console.warn("Error sync rates:", e); }
}
syncRates();

/* ======= MOTOR DE CLIENTES ======= */
(function() {
    const input = document.getElementById('buscar-cliente-id');
    const dropdown = document.getElementById('cliente-dropdown');
    const token = localStorage.getItem('token');

    function closeDropdown() {
        dropdown.style.display = 'none';
        dropdown.innerHTML = '';
    }

    input.addEventListener('input', function() {
        const q = this.value.trim().toLowerCase();
        if (q.length < 1) { closeDropdown(); return; }

        fetch(`${CONFIG.API_BASE_URL}/api/clientes?q=${encodeURIComponent(q)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(matches => {
            dropdown.innerHTML = '';
            if (matches && matches.length > 0) {
                matches.forEach(cliente => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `
                        <div class="autocomplete-info">
                            <div class="autocomplete-name">${cliente.nombre}</div>
                            <div class="autocomplete-subinfo">${cliente.identificacion}</div>
                        </div>
                    `;
                    item.onclick = () => {
                        seleccionarCliente(cliente);
                        closeDropdown();
                    };
                    dropdown.appendChild(item);
                });
                dropdown.style.display = 'block';
            }
        });
    });

    function seleccionarCliente(cli) {
        document.getElementById('cli-nombre').textContent = cli.nombre;
        document.getElementById('cli-full-id').textContent = `${cli.tipo_identificacion || 'ID'} - ${cli.cedula || cli.identificacion}`;
        document.getElementById('cli-provincia').textContent = cli.provincia || '---';
        document.getElementById('cli-canton').textContent = cli.canton || '---';
        document.getElementById('cli-distrito').textContent = cli.distrito || '---';
        document.getElementById('cli-email').textContent = cli.email || cli.correo || '---';
        document.getElementById('cli-telefono').textContent = cli.telefono || '---';
        document.getElementById('cli-regimen').textContent = cli.regimen || 'Régimen General';
        document.getElementById('cli-actividad').textContent = cli.actividad || 'Actividad no especificada';

        document.getElementById('cliente-info-panel').classList.add('visible');
        document.getElementById('manual-prospecto').style.display = 'none';
        input.value = cli.identificacion || cli.cedula;
        window.selectedClientId = cli.id;
    }

    document.addEventListener('click', closeDropdown);
})();

// --- PRODUCTOS ---
(function() {
    const input = document.getElementById('buscar-producto');
    const dropdown = document.getElementById('producto-dropdown');
    const token = localStorage.getItem('token');

    input.addEventListener('input', function() {
        const q = this.value.trim().toLowerCase();
        if (q.length < 1) { dropdown.style.display = 'none'; return; }

        fetch(`${CONFIG.API_BASE_URL}/api/productos?q=${encodeURIComponent(q)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(matches => {
            dropdown.innerHTML = '';
            if (matches && matches.length > 0) {
                matches.forEach(prod => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `
                        <div class="autocomplete-info">
                            <div class="autocomplete-name">${prod.descripcion || prod.nombre}</div>
                            <div class="autocomplete-subinfo">${prod.codigo || ''}</div>
                        </div>
                    `;
                    item.onclick = () => {
                        agregarLinea(prod);
                        input.value = '';
                        dropdown.style.display = 'none';
                    };
                    dropdown.appendChild(item);
                });
                dropdown.style.display = 'block';
            }
        });
    });
})();

let lineCount = 0;
function agregarLinea(prod = null) {
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
    
    if(prod) {
        precio = prod.precio_venta || prod.precio || 0;
        descr = prod.descripcion || prod.nombre || "";
        if(monedaActual === 'USD' && currentRates.usd > 1) precio = precio / currentRates.usd;
    }

    tr.innerHTML = `
        <td><input type="number" class="fi-table cant-i text-center" value="1" min="1" oninput="recalcular()"></td>
        <td><input type="text" class="fi-table desc-i" value="${descr}"></td>
        <td><input type="number" class="fi-table precio-i text-center" value="${precio.toFixed(2)}" oninput="recalcular()"></td>
        <td><input type="number" class="fi-table desc-i text-center" value="0.00" oninput="recalcular()"></td>
        <td style="text-align:right;"><span class="sub-cell" style="font-weight:900;">${symbol}0.00</span></td>
        <td class="text-center">
            <button type="button" onclick="this.closest('tr').remove(); recalcular();" class="btn-delete"><i class="fas fa-trash-alt"></i></button>
        </td>
    `;
    tbody.appendChild(tr);
    recalcular();
}

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

document.getElementById('btn-add-manual').addEventListener('click', () => agregarLinea());

// --- SUBMIT ---
document.getElementById('proforma-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const clienteId = window.selectedClientId;
    const moneda = document.getElementById('moneda').value;
    const notas = document.getElementById('notas-cotizacion').value;
    const vencimiento = document.getElementById('fecha-vencimiento').value;

    const items = [];
    document.querySelectorAll('#detalle-tabla tr:not(#empty-row)').forEach(tr => {
        const inputs = tr.querySelectorAll('input');
        items.push({
            cantidad: inputs[0].value,
            descripcion: inputs[1].value,
            precio_unitario: inputs[2].value,
            descuento: inputs[3].value
        });
    });

    const token = localStorage.getItem('token');
    try {
        const res = await fetch(`${CONFIG.API_BASE_URL}/api/cotizaciones`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                cliente_id: clienteId,
                moneda: moneda,
                notas: notas,
                vencimiento: vencimiento,
                items: items,
                total: parseFloat(document.getElementById('total-final').textContent.replace(/[^\d.-]/g, ''))
            })
        });

        if (res.ok) {
            Swal.fire('¡Éxito!', 'Cotización guardada y generada.', 'success').then(() => {
                // Lógica de PDF aquí (abreviada para brevedad)
                window.location.reload();
            });
        }
    } catch (err) {
        console.error(err);
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