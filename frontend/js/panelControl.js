// Función para cerrar sesión
function cerrarSesion() {
    if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = 'inicioSesion.html';
    }
}

// Animaciones adicionales para el dashboard y carga de datos reales
document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'inicioSesion.html';
        return;
    }
    
    // Verificar que SuperAdmin no pueda acceder a esta pantalla
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.is_superadmin) {
        // Si es SuperAdmin, redirigir a superAdmin.html
        Swal.fire({
            icon: 'error',
            title: 'Acceso Denegado',
            text: 'Los SuperAdministradores deben usar el panel de SuperAdmin.',
            confirmButtonColor: '#ef4444'
        }).then(() => {
            window.location.href = 'superAdmin.html';
        });
        return;
    }

    function renderPlanSummary(userData) {
        const container = document.getElementById('planSummary');
        if (!container) return;

        const planLabel = userData.plan_label || 'Starter';
        const planType = userData.plan_tipo || 'start';
        const planQuota = userData.plan_cuota || 0;
        const planState = (userData.plan_estado || 'activo').toUpperCase();

        container.innerHTML = `
            <div style="min-width:240px;">
                <div class="plan-summary-title">Plan activo</div>
                <h2 class="plan-summary-name">${planLabel}</h2>
            </div>
            <div class="plan-summary-details">
                <div class="plan-summary-item">Tipo: ${planType}</div>
                <div class="plan-summary-item">Cuota: ${planQuota} facturas</div>
                <div class="plan-summary-status">Estado: ${planState}</div>
            </div>
        `;
    }

    renderPlanSummary(user);

    // Filtrar accesos rápidos y botones del header según permisos del usuario
    try {
        const permisos = Array.isArray(user?.pantallas) ? user.pantallas : [];
        // Alias map igual que en sidebar
        const aliasMap = {
            facturacion: ['facturacion', 'pantallaFacturacion'],
            dashboard: ['dashboard', 'panelControl'],
            editarFactura: ['editarFactura'],
            clientes: ['clientes'],
            inventario: ['inventario'],
            auditoria: ['auditoria'],
            notificaciones: ['notificaciones'],
            configuracion: ['configuracion'],
            reportes: ['reportes'],
            cotizaciones: ['cotizaciones'],
            pos: ['pos'],
            registro: ['registro']
        };

        function hasPerm(perms, key) {
            const ids = aliasMap[key] || [key];
            return ids.some(i => perms.includes(i));
        }

        if (!user.is_superadmin) {
            const mapFileToModule = {
                'pantallaFacturacion.html': 'facturacion',
                'clientes.html': 'clientes',
                'inventario.html': 'inventario',
                'editarFactura.html': 'editarFactura',
                'auditoria.html': 'auditoria',
                'notificaciones.html': 'notificaciones',
                'configuracion.html': 'configuracion',
                'reportes.html': 'reportes',
                'cotizaciones.html': 'cotizaciones',
                'pos.html': 'pos',
                'panelControl.html': 'dashboard'
            };

            // Header buttons
            document.querySelectorAll('.header-nav .header-nav-btn').forEach(btn => {
                const onclick = btn.getAttribute('onclick') || '';
                const m = onclick.match(/irA\('([^']+)'\)/);
                if (m) {
                    const file = m[1];
                    const mod = mapFileToModule[file];
                    if (mod && !hasPerm(permisos, mod)) btn.style.display = 'none';
                }
            });

            // Quick-access cards
            document.querySelectorAll('.quick-access-card').forEach(card => {
                const onclick = card.getAttribute('onclick') || '';
                const m = onclick.match(/irA\('([^']+)'\)/);
                if (m) {
                    const file = m[1];
                    const mod = mapFileToModule[file];
                    if (mod && !hasPerm(permisos, mod)) card.style.display = 'none';
                }
            });
        }
    } catch (e) { console.error('Error aplicando filtro de permisos en panelControl:', e); }

    // Cargar datos reales del API
    // Cargar datos reales del API
    async function cargarDashboard() {
        try {
            const res = await fetch(`${CONFIG.API_BASE_URL}/api/dashboard`, {
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            const data = await res.json();
            
            if (res.ok) {
                // Actualizar contadores
                const updateVal = (id, val) => {
                    const el = document.getElementById(id);
                    if (el) el.textContent = val;
                };

                const formatM = (num) => {
                    if (num >= 1000000) return '₡' + (num / 1000000).toFixed(1) + 'M';
                    return '₡' + num.toLocaleString();
                };

                updateVal('dash-facturas', data.facturasEmitidas || 0);
                updateVal('dash-ingresos', formatM(data.ingresosTotales || 0));
                updateVal('dash-clientes', data.clientesActivos || 0);
                updateVal('dash-conversion', data.tasaConversion || '0.0%');

                // Actualizar variaciones con iconos dinámicos
                const updateVar = (id, val) => {
                    const el = document.getElementById(id);
                    if (el) {
                        const isPositive = val.startsWith('+');
                        const isNegative = val.startsWith('-');
                        const icon = isPositive ? 'fa-arrow-up' : (isNegative ? 'fa-arrow-down' : 'fa-minus');
                        const color = isPositive ? '#10b981' : (isNegative ? '#ef4444' : '#64748b');
                        el.innerHTML = `<i class="fas ${icon}" style="color: ${color};"></i> ${val}`;
                        el.style.color = color;
                    }
                };
                updateVar('var-facturas', data.facturasVariacion || '0%');
                updateVar('var-ingresos', data.ingresosVariacion || '0%');
                updateVar('var-clientes', data.clientesVariacion || '0%');
                updateVar('var-exito', data.tasaVariacion || '0%');

                // Actualizar actividad reciente
                const tbody = document.getElementById('activity-list');
                if (tbody && data.actividadReciente) {
                    tbody.innerHTML = '';
                    data.actividadReciente.forEach((item, index) => {
                        const tr = document.createElement('tr');
                        tr.style.setProperty('--row-index', index);
                        
                        let badgeClass = 'status-pendiente';
                        const estado = (item.estado || '').toLowerCase();
                        if(estado.includes('pagada') || estado.includes('aceptada') || estado.includes('éxito')) badgeClass = 'status-aceptado';
                        if(estado.includes('vencida') || estado.includes('anulada') || estado.includes('rechazada')) badgeClass = 'status-rechazado';
                        
                        const fecha = new Date(item.fecha).toLocaleDateString('es-CR', {day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'});
                        
                        tr.innerHTML = `
                            <td class="activity-client">
                                <div style="display:flex; align-items:center; gap:10px;">
                                    <div style="width:32px; height:32px; border-radius:50%; background:#f1f5f9; display:flex; align-items:center; justify-content:center; color:#1e3a8a; font-weight:900; font-size:0.7rem;">${item.clienteNombre.charAt(0)}</div>
                                    <span>${item.clienteNombre}</span>
                                </div>
                            </td>
                            <td style="font-family:monospace; font-weight:700; color:#64748b;">${item.id}</td>
                            <td class="activity-amount" style="font-weight:900; color:#0f172a;">₡${(item.monto || 0).toLocaleString('es-CR')}</td>
                            <td><span class="stat-badge ${badgeClass}">${item.estado || 'Procesando'}</span></td>
                            <td style="color:#64748b; font-size:0.85rem;">${fecha}</td>
                            <td>
                                <button class="btn-action" title="Ver Detalle" onclick="Swal.fire('Info', 'Visualización de documento: ' + '${item.id}', 'info')">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            } else if (res.status === 401) {
                localStorage.clear();
                window.location.href = 'inicioSesion.html';
            }
        } catch (err) {
            console.error("Error al cargar dashboard:", err);
        }
    }

    cargarDashboard();
    setInterval(cargarDashboard, 15000);

    // --- Lógica del Tipo de Cambio (Original de Hacienda) ---
    async function actualizarTipoCambio() {
        const urlDirecta = "https://api.hacienda.go.cr/indicadores/tc";
        const urlProxy = "proxy_hacienda.php"; 
        const labelStatus = document.getElementById('dash-tc-label');
        let data = null;
        
        try {
            const resProxy = await fetch(urlProxy);
            if (resProxy.ok) data = await resProxy.json();
        } catch (e) { console.warn("Proxy no disponible"); }

        if (!data) {
            try {
                const resDirecta = await fetch(urlDirecta);
                if (resDirecta.ok) data = await resDirecta.json();
            } catch (e) { console.error("Error API Hacienda"); }
        }

        if (data) {
            if (data.dolar) {
                const compra = data.dolar.compra.valor;
                const venta = data.dolar.venta.valor;
                if (document.getElementById('dash-usd-compra')) document.getElementById('dash-usd-compra').textContent = `₡${compra.toFixed(2)}`;
                if (document.getElementById('dash-usd-venta')) document.getElementById('dash-usd-venta').textContent = `₡${venta.toFixed(2)}`;
                
                const fCompra = data.dolar.compra.fecha.split('-').reverse().join('/');
                const fVenta = data.dolar.venta.fecha.split('-').reverse().join('/');
                if (document.getElementById('fecha-usd-compra')) document.getElementById('fecha-usd-compra').textContent = fCompra;
                if (document.getElementById('fecha-usd-venta')) document.getElementById('fecha-usd-venta').textContent = fVenta;
            } 
            
            if (data.euro) {
                if (document.getElementById('dash-euro-colones')) document.getElementById('dash-euro-colones').textContent = `₡${data.euro.colones.toFixed(2)}`;
                if (document.getElementById('dash-euro-dolares')) document.getElementById('dash-euro-dolares').textContent = `$${data.euro.dolares.toFixed(4)}`;
                
                const fEuro = data.euro.fecha.split('-').reverse().join('/');
                if (document.getElementById('fecha-euro')) document.getElementById('fecha-euro').textContent = fEuro;
                if (document.getElementById('fecha-euro-usd')) document.getElementById('fecha-euro-usd').textContent = fEuro;
            }

            if (labelStatus && labelStatus.querySelector('span')) {
                labelStatus.style.background = '#ecfdf5';
                labelStatus.style.borderColor = '#bbf7d0';
                labelStatus.style.color = '#10b981';
                labelStatus.querySelector('span').innerHTML = `<i class="fas fa-check-circle"></i> Sincronizado`;
            }
        } else if (labelStatus && labelStatus.querySelector('span')) {
            labelStatus.style.background = '#fef2f2';
            labelStatus.style.borderColor = '#fecaca';
            labelStatus.style.color = '#ef4444';
            labelStatus.querySelector('span').textContent = 'Error API';
        }
    }

    actualizarTipoCambio();
    setInterval(actualizarTipoCambio, 1800000); // 30 min

    // Animar contadores de estadísticas
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            
            if (element.textContent.includes('M')) {
                element.textContent = '₡' + (current / 1000000).toFixed(1) + 'M';
            } else if (element.textContent.includes('₡')) {
                element.textContent = '₡' + Math.floor(current).toLocaleString();
            } else {
                element.textContent = Math.floor(current).toLocaleString();
            }
        }, 16);
    }
    
    // Iniciar animaciones cuando los elementos sean visibles
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const metricValue = entry.target.querySelector('.metric-value');
                if (metricValue && !metricValue.animated) {
                    metricValue.animated = true;
                    const text = metricValue.textContent;
                    const number = parseFloat(text.replace(/[^0-9.]/g, ''));
                     
                    if (!isNaN(number)) {
                        animateCounter(metricValue, number);
                    }
                }
            }
        });
    });
    
    document.querySelectorAll('.metric-item').forEach(item => {
        observer.observe(item);
    });
});

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
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x > canvas.width) this.x = 0;
        if (this.x < 0) this.x = canvas.width;
        if (this.y > canvas.height) this.y = 0;
        if (this.y < 0) this.y = canvas.height;
    }
    draw() {
        ctx.fillStyle = `rgba(255, 255, 255, ${this.opacity})`;
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
                ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 * (1 - dist / 150)})`;
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