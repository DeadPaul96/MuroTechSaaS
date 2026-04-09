(function() {
            const db = window.muroDB;
            let currentFilter = 'all';

            // Mock Data Generator if DB doesn't have enough
            const seedNotifs = [
                { id: 1, type:'hacienda', icon:'fas fa-university', title:'Factura FE-00249 Aceptada', desc:'El Ministerio de Hacienda ha confirmado la recepción exitosa del comprobante.', time:'Hace 2 min', read: false },
                { id: 2, type:'inventario', icon:'fas fa-exclamation-triangle', title:'Stock Crítico: Mouse Logitech', desc:'Solo quedan 2 unidades en almacén. Se recomienda solicitar pedido al proveedor.', time:'Hace 15 min', read: false },
                { id: 3, type:'sistema', icon:'fas fa-sync-alt', title:'Actualización v6.2.1', desc:'Hemos optimizado el motor de búsqueda de productos. Ahora es un 40% más rápido.', time:'Hace 1 hora', read: false },
                { id: 4, type:'hacienda', icon:'fas fa-times-circle', title:'Error en Ticket Electrónico', desc:'No se pudo enviar el ticket TE-00042 por error de firma. Intente reenviar.', time:'Hace 3 horas', read: true },
                { id: 5, type:'pago', icon:'fas fa-wallet', title:'Pago SINPE Recibido', desc:'Se detectó un ingreso de ₡12,500 de DANIEL MORA. Referencia: 45892.', time:'Hace 5 horas', read: false },
                { id: 6, type:'sistema', icon:'fas fa-shield-alt', title:'Cierre de Caja Exitoso', desc:'La caja #01 fue cerrada correctamente por admin. Sobrante: ₡0.', time:'Ayer 8:45 PM', read: true }
            ];

            // Globalize markAllRead for the header button
            window.markAllRead = function() {
                seedNotifs.forEach(n => n.read = true);
                render();
                Swal.fire({ 
                    toast: true, 
                    position: 'top-end', 
                    icon:'success', 
                    title: 'Todas marcadas como leídas', 
                    showConfirmButton: false, 
                    timer: 2000 
                });
            };

            function render() {
                const container = document.getElementById('notif-container');
                if (!container) return; // Guard clause

                const filtered = currentFilter === 'all' 
                    ? seedNotifs 
                    : seedNotifs.filter(n => n.type === currentFilter);

                container.innerHTML = '';

                if (filtered.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state" style="text-align:center; padding:60px 20px; color:#94a3b8;">
                            <i class="fas fa-bell-slash" style="font-size:3rem; opacity:0.2; margin-bottom:15px; display:block;"></i>
                            <h3 style="font-weight:700; color:#64748b;">No hay notificaciones</h3>
                            <p style="font-size:0.9rem;">No tienes alertas en la categoría "${currentFilter}"</p>
                        </div>
                    `;
                    updateStats();
                    return;
                }

                filtered.forEach(n => {
                    const item = document.createElement('div');
                    item.className = `notif-item ${n.read ? '' : 'unread'}`;
                    item.innerHTML = `
                        <div class="notif-icon icon-${n.type}">
                            <i class="${n.icon}"></i>
                        </div>
                        <div class="notif-content">
                            <div class="notif-title">${n.title}</div>
                            <div class="notif-desc">${n.desc}</div>
                            <div class="notif-meta">
                                <span><i class="far fa-clock"></i> ${n.time}</span>
                                <span style="text-transform:uppercase;">• ${n.type}</span>
                            </div>
                        </div>
                    `;
                    item.onclick = () => {
                        n.read = true;
                        render();
                    };
                    container.appendChild(item);
                });

                updateStats();
            }

            function updateStats() {
                const unread = seedNotifs.filter(n => !n.read).length;
                const unreadEl = document.getElementById('unread-count');
                if (unreadEl) {
                    unreadEl.textContent = `${unread} Sin Leer`;
                    unreadEl.style.display = unread > 0 ? 'flex' : 'none';
                }
            }

            // Events
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.onclick = function() {
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentFilter = this.dataset.filter;
                    render();
                };
            });

            render();
        })();
    


        const canvas = document.getElementById('particles-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const particles = [];
        class Particle {
            constructor() { this.x = Math.random() * canvas.width; this.y = Math.random() * canvas.height; this.size = Math.random() * 2 + 0.5; this.speedX = Math.random() * 0.5 - 0.25; this.speedY = Math.random() * 0.5 - 0.25; this.opacity = Math.random() * 0.5 + 0.1; }
            update() { this.x += this.speedX; this.y += this.speedY; if (this.x > canvas.width) this.x = 0; if (this.x < 0) this.x = canvas.width; if (this.y > canvas.height) this.y = 0; if (this.y < 0) this.y = canvas.height; }
            draw() { ctx.fillStyle = `rgba(255, 255, 255, ${this.opacity})`; ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fill(); }
        }
        for (let i = 0; i < 60; i++) particles.push(new Particle());
        function animate() { ctx.clearRect(0,0,canvas.width,canvas.height); particles.forEach(p => { p.update(); p.draw(); }); requestAnimationFrame(animate); }
        animate();