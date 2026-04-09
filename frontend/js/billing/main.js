/**
 * MUROTECH POS - Lógica de Facturación 4.4
 * Desarrollado para cumplir con los estándares de Hacienda de Costa Rica.
 */

// --- Estado Global de la Ventas ---
let cart = [];
let docType = '01'; // 01: FE, 04: TE
let currency = 'CRC';
let exchangeRate = 525.0; // Mock del BCCR
let activeReceptor = null;
let activeEconomicActivity = "";

// --- Inicialización ---
document.addEventListener('DOMContentLoaded', () => {
    inicializarSelectores();
    inicializarBuscadorCABYS();
    inicializarBuscadorReceptor();
    cargarActividadesEmisor();
    actualizarTotalesUI();
    
    // Listener para el botón de emisión
    const btnEmitir = document.getElementById('btn-emitir-factura');
    if (btnEmitir) btnEmitir.addEventListener('click', emitirComprobante);
});

/**
 * Configura los selectores premium (Sincronizado con estilo Registro)
 */
function inicializarSelectores() {
    // Tipo de Documento
    const selectDoc = document.getElementById('doc-type-select');
    if (selectDoc) {
        selectDoc.addEventListener('change', (e) => {
            docType = e.target.value;
            console.log('Tipo de documento:', docType);
            const receptorSearch = document.getElementById('pos-receptor-search');
            if (receptorSearch) {
                receptorSearch.placeholder = (docType === '04') ? 
                    "Número de Cédula (Opcional)..." : "Número de Cédula (Requerido)...";
            }
        });
    }

    // Moneda
    const selectCur = document.getElementById('currency-select');
    if (selectCur) {
        selectCur.addEventListener('change', (e) => {
            currency = e.target.value;
            actualizarTotalesUI();
        });
    }
}

/**
 * Carga las actividades económicas del emisor desde el localstorage
 */
function cargarActividadesEmisor() {
    const selector = document.getElementById('pos-actividad-economica');
    const datosContribuyente = JSON.parse(localStorage.getItem('datosContribuyente') || '{}');
    
    const actividades = datosContribuyente.actividades || [
        { codigo: "722001", nombre: "Servicios de Consultoría en Informática" },
        { codigo: "474101", nombre: "Venta de Computadoras y Programas" }
    ];

    if (selector) {
        selector.innerHTML = actividades.map(a => 
            `<option value="${a.codigo}">${a.codigo} - ${a.nombre}</option>`
        ).join('');
        
        activeEconomicActivity = actividades[0]?.codigo || "";
        selector.addEventListener('change', (e) => activeEconomicActivity = e.target.value);
    }
}

// --- Gestión de CAByS y Carrito ---

function inicializarBuscadorCABYS() {
    const input = document.getElementById('pos-cabys-search');
    const dropdown = document.getElementById('cabys-results-dropdown');
    let debounceTimer;

    if (!input) return;

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const query = input.value.trim();
        
        if (query.length < 3) {
            if (dropdown) dropdown.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(async () => {
            const results = [
                { codigo: "1234567890123", descripcion: "Servicio Profesional TI", impuesto: 13, precio: 50000 },
                { codigo: "9876543210123", descripcion: "Licencia Software SaaS", impuesto: 13, precio: 120000 },
                { codigo: "5555544443332", descripcion: "Consultoría Estratégica", impuesto: 1, precio: 75000 }
            ].filter(p => p.descripcion.toLowerCase().includes(query.toLowerCase()) || p.codigo.includes(query));
            renderizarResultadosCABYS(results);
        }, 300);
    });
}

function renderizarResultadosCABYS(productos) {
    const dropdown = document.getElementById('cabys-results-dropdown');
    if (!dropdown) return;

    dropdown.innerHTML = productos.map(p => `
        <div class="search-item" onclick='agregarAlCarrito(${JSON.stringify(p)})'>
            <div style="font-weight:600;">${p.descripcion}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">
                Code: ${p.codigo} | IVA: ${p.impuesto}% | Base: ₡${p.precio.toLocaleString()}
            </div>
        </div>
    `).join('');
    dropdown.style.display = productos.length ? 'block' : 'none';
}

window.agregarAlCarrito = function(producto) {
    const itemExistente = cart.find(i => i.codigo === producto.codigo);
    if (itemExistente) { itemExistente.cantidad += 1; } 
    else { cart.push({ ...producto, cantidad: 1, descuento: 0 }); }

    const input = document.getElementById('pos-cabys-search');
    const dropdown = document.getElementById('cabys-results-dropdown');
    if (input) input.value = "";
    if (dropdown) dropdown.style.display = 'none';
    
    actualizarCarritoUI();
    Swal.fire({ toast: true, position: 'bottom-end', icon: 'success', title: 'Ítem agregado', showConfirmButton: false, timer: 1500 });
};

function actualizarCarritoUI() {
    const tbody = document.getElementById('pos-cart-body');
    if (!tbody) return;

    if (cart.length === 0) {
        tbody.innerHTML = `<tr id="empty-cart-msg"><td colspan="6" style="text-align: center; padding: 50px; color: var(--text-muted);"><i class="fas fa-plus-circle" style="font-size: 2rem; display: block; margin-bottom: 10px; opacity: 0.2;"></i>Agregue productos para iniciar</td></tr>`;
        actualizarTotalesUI();
        return;
    }

    tbody.innerHTML = cart.map((item, index) => {
        const subtotal = item.precio * item.cantidad;
        const total = subtotal * (1 + (item.impuesto / 100));
        return `
            <tr>
                <td>${item.descripcion}<br><small style="color:var(--text-muted);">${item.codigo}</small></td>
                <td style="text-align:center;"><input type="number" value="${item.cantidad}" class="premium-input" style="width:60px; padding:5px; text-align:center;" onchange="actualizarCantidad(${index}, this.value)"></td>
                <td style="text-align:right;">₡${item.precio.toLocaleString()}</td>
                <td style="text-align:center;">${item.impuesto}%</td>
                <td style="text-align:right;"><strong>₡${total.toLocaleString()}</strong></td>
                <td style="text-align:center;"><i class="fas fa-times" style="color:var(--danger); cursor:pointer;" onclick="eliminarItem(${index})"></i></td>
            </tr>
        `;
    }).join('');
    actualizarTotalesUI();
}

window.actualizarCantidad = function(index, value) {
    const cant = parseFloat(value);
    if (cant > 0) { cart[index].cantidad = cant; actualizarCarritoUI(); }
};

window.eliminarItem = function(index) {
    cart.splice(index, 1);
    actualizarCarritoUI();
};

function actualizarTotalesUI() {
    let subtotal = 0, totalIVA = 0;
    cart.forEach(item => {
        const lineSubtotal = item.precio * item.cantidad;
        subtotal += lineSubtotal;
        totalIVA += lineSubtotal * (item.impuesto / 100);
    });

    const factor = (currency === 'USD') ? (1 / exchangeRate) : 1;
    const prefix = (currency === 'USD') ? '$' : '₡';

    const elSub = document.getElementById('pos-sum-subtotal');
    const elTax = document.getElementById('pos-sum-tax');
    const elTot = document.getElementById('pos-sum-total');

    if (elSub) elSub.innerText = `${prefix}${(subtotal * factor).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    if (elTax) elTax.innerText = `${prefix}${(totalIVA * factor).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    if (elTot) elTot.innerText = `${prefix}${( (subtotal + totalIVA) * factor).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
}

// --- Receptor Smart ---

function inicializarBuscadorReceptor() {
    const input = document.getElementById('pos-receptor-search');
    if (!input) return;
    input.addEventListener('input', (e) => detectIdType(e.target.value));
}

window.detectIdType = function(val) {
    const badge = document.getElementById('id-detection-badge');
    if (!badge) return;
    
    const cleanVal = val.replace(/\D/g, '');
    if (cleanVal.length === 9) { badge.innerText = "Física"; badge.style.background = "#0ea5e9"; }
    else if (cleanVal.length === 10) { badge.innerText = "Jurídica"; badge.style.background = "#8b5cf6"; }
    else if (cleanVal.length >= 11) { badge.innerText = "DIMEX/NITE"; badge.style.background = "#10b981"; }
    else { badge.innerText = "Detección Automática"; badge.style.background = "#94a3b8"; }
};

window.setGenericClient = function() {
    const nombre = document.getElementById('pos-receptor-nombre');
    const cedula = document.getElementById('pos-receptor-search');
    const email = document.getElementById('pos-receptor-email');
    if (nombre) nombre.value = "CLIENTE CONTADO / GENERICO";
    if (cedula) cedula.value = "000000000";
    if (email) email.value = "generico@murotech.cr";
    detectIdType("000000000");
};

async function emitirComprobante() {
    if (cart.length === 0) { Swal.fire('Error', 'El carrito está vacío', 'warning'); return; }
    
    const { value: confirm } = await Swal.fire({
        title: '¿Confirmar Facturación?',
        text: `Total: ${document.getElementById('pos-sum-total').innerText}`,
        icon: 'question', showCancelButton: true, confirmButtonText: 'Sí, Emitir'
    });

    if (confirm) {
        Swal.fire({ title: 'Procesando Hacienda...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });
        setTimeout(() => {
            Swal.fire('¡Éxito!', 'Comprobante emitido correctamente', 'success').then(() => {
                cart = []; actualizarCarritoUI();
            });
        }, 2000);
    }
}
