/* --- Lógica para el Módulo de Notificaciones --- */

document.addEventListener('DOMContentLoaded', () => {
    loadNotifications();
});

// Datos de ejemplo para las notificaciones
const demoNotifications = [
    {
        id: 1,
        title: "Factura Aceptada por Hacienda",
        body: "La factura electrónica 00100001010000000045 ha sido aceptada exitosamente por el Ministerio de Hacienda.",
        type: "mh",
        time: "Hace 5 minutos",
        unread: true,
        icon: "fas fa-check-circle"
    },
    {
        id: 2,
        title: "Stock Bajo: Papel Térmico",
        body: "Solo quedan 5 rollos de papel térmico en bodega. Se recomienda realizar un pedido pronto.",
        type: "inventory",
        time: "Hace 2 horas",
        unread: true,
        icon: "fas fa-exclamation-triangle"
    },
    {
        id: 3,
        title: "Actualización de Sistema v6.1",
        body: "Se han implementado mejoras en la velocidad de carga de reportes y corrección de errores menores.",
        type: "system",
        time: "Ayer, 04:30 PM",
        unread: false,
        icon: "fas fa-sync-alt"
    },
    {
        id: 4,
        title: "Error de Conexión MH",
        body: "Se detectó un tiempo de espera excedido al intentar conectar con los servidores de Hacienda. Reintentando...",
        type: "danger",
        time: "Ayer, 09:12 AM",
        unread: false,
        icon: "fas fa-times-circle"
    }
];

function loadNotifications() {
    const container = document.getElementById('notif-list');
    if (!container) return;

    container.innerHTML = '';

    demoNotifications.forEach(notif => {
        const item = document.createElement('div');
        item.className = `notification-item ${notif.unread ? 'unread' : ''}`;
        item.onclick = () => markAsRead(notif.id);

        item.innerHTML = `
            <div class="notif-icon-container type-${notif.type}">
                <i class="${notif.icon}"></i>
            </div>
            <div class="notif-content">
                <div class="notif-header">
                    <span class="notif-title">${notif.title}</span>
                    <span class="notif-time">${notif.time}</span>
                </div>
                <div class="notif-body">${notif.body}</div>
                <div class="notif-actions">
                    <button class="notif-btn">Ver detalle</button>
                    ${notif.unread ? `<button class="notif-btn" onclick="event.stopPropagation(); markAsRead(${notif.id})">Marcar como leída</button>` : ''}
                    <button class="notif-btn" style="color: #ef4444;" onclick="event.stopPropagation(); deleteNotif(${notif.id})">Eliminar</button>
                </div>
            </div>
        `;
        container.appendChild(item);
    });
}

function markAsRead(id) {
    console.log(`Marcando notificación ${id} como leída`);
    // En un entorno real, aquí se llamaría a la API
    const index = demoNotifications.findIndex(n => n.id === id);
    if (index !== -1) {
        demoNotifications[index].unread = false;
        loadNotifications();
    }
}

function deleteNotif(id) {
    if (confirm('¿Eliminar esta notificación?')) {
        const index = demoNotifications.findIndex(n => n.id === id);
        if (index !== -1) {
            demoNotifications.splice(index, 1);
            loadNotifications();
        }
    }
}

function marcarTodasLeidas() {
    demoNotifications.forEach(n => n.unread = false);
    loadNotifications();
}
