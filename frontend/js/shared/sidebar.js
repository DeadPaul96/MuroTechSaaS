document.addEventListener('DOMContentLoaded', () => {
  const aside = document.querySelector('aside.sidebar');
  if (!aside) return;

  const path = (location.pathname || '').toLowerCase();
  
  // Robust check for active state
  const isActive = (file) => {
    const normalizedFile = file.toLowerCase().replace('.html', '');
    const normalizedPath = path.replace('.html', '');
    
    // Caso especial para Dashboard
    if (normalizedFile === 'dashboard' && normalizedPath.endsWith('panelcontrol')) return true;
    
    return normalizedPath.endsWith('/' + normalizedFile) || 
           normalizedPath.endsWith('\\' + normalizedFile) || 
           normalizedPath === normalizedFile;
  };

  const btn = (target, icon, title, onclick, activeFile = target) => `
    <button class="sidebar-btn ${isActive(activeFile) ? 'active' : ''}" onclick="${onclick}" data-title="${title}">
      <i class="${icon}"></i>
      <span style="display: none;">${title}</span>
    </button>`;

  // Obtener permisos del usuario desde el localStorage
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  const permisos = Array.isArray(user?.pantallas) ? user.pantallas : [];

  // Alias entre identificadores frontend/backend (históricos)
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
    mensajeReceptor: ['mensajeReceptor'],
    pos: ['pos'],
    registro: ['registro']
  };

  function hasPerm(perms, key) {
    const ids = aliasMap[key] || [key];
    return ids.some(i => perms.includes(i));
  }
  
  // Modo Invitado/Local (para cuando se abren los archivos directamente o no hay login)
  const isLocal = location.protocol === 'file:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  const showAll = !user || user?.is_superadmin || (isLocal && !user);

  const renderButtons = () => {
    // 1. Dashboard
    let html = btn('panelControl.html', 'fas fa-th-large', 'Dashboard', "irA('panelControl.html')", 'dashboard');
    
    // Separador después de Dashboard
    html += '<hr style="width: 20px; border: 0; border-top: 1px solid rgba(0,0,0,0.05); margin: 8px auto; opacity: 0.5;">';
    
    // 2. Módulos principales
    const mainModules = [
      { id: 'facturacion', file: 'pantallaFacturacion.html', icon: 'fas fa-file-invoice-dollar', title: 'Facturación' },
      { id: 'clientes', file: 'clientes.html', icon: 'fas fa-users', title: 'Clientes' },
      { id: 'inventario', file: 'inventario.html', icon: 'fas fa-boxes', title: 'Inventario' },
      { id: 'editarFactura', file: 'editarFactura.html', icon: 'fas fa-edit', title: 'Editar Factura' },
      { id: 'auditoria', file: 'auditoria.html', icon: 'fas fa-search', title: 'Auditoría' },
      { id: 'notificaciones', file: 'notificaciones.html', icon: 'fas fa-bell', title: 'Notificaciones' },
      { id: 'configuracion', file: 'configuracion.html', icon: 'fas fa-user-shield', title: 'Administrador' }
    ];

    mainModules.forEach(m => {
      if (showAll || hasPerm(permisos, m.id)) {
        html += btn(m.file, m.icon, m.title, `irA('${m.file}')`);
      }
    });

    // Separador antes de Reportes
    html += '<hr style="width: 20px; border: 0; border-top: 1px solid rgba(0,0,0,0.05); margin: 8px auto; opacity: 0.5;">';

    // 3. Módulos secundarios
    const secondModules = [
      { id: 'reportes', file: 'reportes.html', icon: 'fas fa-chart-line', title: 'Reportes' },
      { id: 'cotizaciones', file: 'cotizaciones.html', icon: 'fas fa-file-signature', title: 'Cotizaciones' },
      { id: 'mensajeReceptor', file: 'mensajeReceptor.html', icon: 'fas fa-envelope-open-text', title: 'Mensaje Receptor' }
    ];

    secondModules.forEach(m => {
      if (showAll || hasPerm(permisos, m.id)) {
        html += btn(m.file, m.icon, m.title, `irA('${m.file}')`);
      }
    });

    return html;
  };

  aside.innerHTML = `
    <div class="sidebar-section">
      <div class="sidebar-pill" id="sidebar-pill" style="opacity: 0;"></div>
      ${renderButtons()}
    </div>
  `;

  // Posicionar el Pill inicialmente (sin lag visual)
  const setInitialPill = () => {
    const activeBtn = aside.querySelector('.sidebar-section .sidebar-btn.active');
    const pill = document.getElementById('sidebar-pill');
    if (activeBtn && pill) {
      // Desactivar transición momentáneamente para el salto inicial
      pill.style.transition = 'none';
      pill.style.top = `${activeBtn.offsetTop}px`;
      
      // Forzar Reflow
      pill.offsetHeight;
      
      // Restaurar transición y mostrar
      pill.style.transition = 'all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
      pill.style.opacity = '1';
    }
  };

  // Ejecutar lo más pronto posible
  if (document.readyState === 'complete') {
    setInitialPill();
  } else {
    window.addEventListener('load', setInitialPill);
  }

  // Mover el Pill al hacer click (efecto viaje)
  aside.addEventListener('click', (e) => {
    const btn = e.target.closest('.sidebar-btn');
    if (btn) {
      const pill = document.getElementById('sidebar-pill');
      if (pill) {
        pill.style.transition = 'all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
        pill.style.top = `${btn.offsetTop}px`;
        pill.style.opacity = '1';
      }
    }
  });
});
