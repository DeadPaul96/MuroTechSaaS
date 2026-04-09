document.addEventListener('DOMContentLoaded', () => {
  const aside = document.querySelector('aside.sidebar');
  if (!aside) return;

  const path = (location.pathname || '').toLowerCase();
  
  // Robust check for active state
  const isActive = (file) => {
    const normalizedFile = file.toLowerCase().replace('.html', '');
    const normalizedPath = path.replace('.html', '');
    return normalizedPath.endsWith('/' + normalizedFile) || normalizedPath.endsWith('\\' + normalizedFile);
  };

  const btn = (target, icon, title, onclick, activeFile = target) => `
    <button class="sidebar-btn ${isActive(activeFile) ? 'active' : ''}" onclick="${onclick}" data-title="${title}">
      <i class="${icon}"></i>
      <span style="display: none;">${title}</span>
    </button>`;

  aside.innerHTML = `
    <div class="sidebar-pill" id="sidebar-pill" style="opacity: 0;"></div>
    <div class="sidebar-section">
      ${btn('panelControl.html', 'fas fa-th-large', 'Dashboard', "irA('panelControl.html')")}
      <hr style="width: 25px; border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 5px 0;">
      ${btn('pantallaFacturacion.html', 'fas fa-file-invoice-dollar', 'Facturación', "irA('pantallaFacturacion.html')")}
      ${btn('clientes.html', 'fas fa-users', 'Clientes', "irA('clientes.html')")}
      ${btn('inventario.html', 'fas fa-boxes', 'Inventario', "irA('inventario.html')")}
      ${btn('editarFactura.html', 'fas fa-edit', 'Editar Factura', "irA('editarFactura.html')")}
      ${btn('auditoria.html', 'fas fa-search', 'Auditoría', "irA('auditoria.html')")}
      ${btn('notificaciones.html', 'fas fa-bell', 'Notificaciones', "irA('notificaciones.html')")}
      ${btn('configuracion.html', 'fas fa-user-shield', 'Administrador', "irA('configuracion.html')")}
      <hr style="width: 25px; border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 5px 0;">
      ${btn('reportes.html', 'fas fa-chart-line', 'Reportes', "irA('reportes.html')")}
      ${btn('cotizaciones.html', 'fas fa-file-signature', 'Cotizaciones', "irA('cotizaciones.html')")}
    </div>
    
    <div class="sidebar-section" style="margin-top: auto; padding-bottom: 5px;">
      ${btn('logout', 'fas fa-power-off', 'Cerrar Sesión', "cerrarSesion()", "logout")}
    </div>
  `;

  // Posicionar el Pill inicialmente (sin lag visual)
  const setInitialPill = () => {
    const activeBtn = aside.querySelector('.sidebar-btn.active');
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
