// Función para cerrar sesión
function cerrarSesion() {
    if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = 'inicioSesion.html';
    }
}

// Animaciones adicionales para el dashboard y carga de MockDB
document.addEventListener('DOMContentLoaded', function() {
    // Cargar datos del MockDB
    if (window.muroDB) {
        const metricas = muroDB.getMetricasDashboard();
        document.getElementById('dash-facturas').textContent = metricas.facturasEmitidas;
        document.getElementById('dash-ingresos').textContent = metricas.ingresosTotales;
        document.getElementById('dash-clientes').textContent = metricas.clientesActivos;
        document.getElementById('dash-conversion').textContent = metricas.tasaConversion;

        const tbody = document.getElementById('activity-list');
        tbody.innerHTML = '';
        const facturas = muroDB.getFacturas().slice(0, 5); // Últimas 5
        
        facturas.forEach((fac, index) => {
            const tr = document.createElement('tr');
            tr.style.setProperty('--row-index', index);
            
            let badgeClass = 'status-pendiente';
            if(fac.estado === 'Pagada') badgeClass = 'status-aceptado';
            if(fac.estado === 'Vencida' || fac.estado === 'Anulada') badgeClass = 'status-rechazado';
            
            const dateObj = new Date(fac.fecha);
            const fecha = dateObj.toLocaleDateString('es-CR', {day:'2-digit', month:'short', year:'numeric'});
            
            tr.innerHTML = `
                <td class="activity-client">${fac.clienteNombre}</td>
                <td>${fac.id}</td>
                <td class="activity-amount">₡${fac.monto.toLocaleString('es-CR')}</td>
                <td><span class="stat-badge ${badgeClass}">${fac.estado}</span></td>
                <td>${fecha}</td>
                <td>
                    <button class="btn-action" title="Ver Detalle">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // --- Lógica del Tipo de Cambio Sincronizada (USD/EUR) ---
    async function actualizarTipoCambio() {
        const urlDirecta = "https://api.hacienda.go.cr/indicadores/tc";
        const labelStatus = document.getElementById('dash-tc-label');
        let data = null;
        
        try {
            const resDirecta = await fetch(urlDirecta);
            if (resDirecta.ok) data = await resDirecta.json();
        } catch (e) { 
            console.error("Error API Hacienda"); 
        }

        if (data && data.dolar) {
            const venta = data.dolar.venta.valor;
            const compra = data.dolar.compra.valor;
            
            // Actualizar USD
            if (document.getElementById('dash-usd-compra')) document.getElementById('dash-usd-compra').textContent = `₡${compra.toFixed(2)}`;
            if (document.getElementById('dash-usd-venta')) document.getElementById('dash-usd-venta').textContent = `₡${venta.toFixed(2)}`;
            
            const fUSD = data.dolar.venta.fecha.split('-').reverse().join('/');
            if (document.getElementById('fecha-usd-compra')) document.getElementById('fecha-usd-compra').textContent = fUSD;
            if (document.getElementById('fecha-usd-venta')) document.getElementById('fecha-usd-venta').textContent = fUSD;

            // Sincronización de EURO (Consistente con Pantalla de Facturación)
            const euroSimulado = Math.round((venta * 1.10) * 100) / 100;
            const euroDolarSimulado = 1.1000;

            if (document.getElementById('dash-euro-colones')) document.getElementById('dash-euro-colones').textContent = `₡${euroSimulado.toFixed(2)}`;
            if (document.getElementById('dash-euro-dolares')) document.getElementById('dash-euro-dolares').textContent = `$${euroDolarSimulado.toFixed(4)}`;
            
            if (document.getElementById('fecha-euro')) document.getElementById('fecha-euro').textContent = fUSD;
            if (document.getElementById('fecha-euro-usd')) document.getElementById('fecha-euro-usd').textContent = fUSD;

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