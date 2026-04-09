let carrito = [];
        const formatter = new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', minimumFractionDigits: 0 });

        // Cargar productos del inventario (mockDB)
        function cargarProductos(filtro = '') {
            const grid = document.querySelector('.products-grid');
            const productos = window.muroDB ? window.muroDB.getProductos() : [];
            const iconos = ['fas fa-laptop','fas fa-desktop','fas fa-print','fas fa-mouse','fas fa-keyboard','fas fa-hdd','fas fa-headphones','fas fa-shield-alt','fas fa-memory','fas fa-plug','fas fa-tools','fas fa-box'];
            const colores = ['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444','#06b6d4','#ec4899','#14b8a6','#6366f1','#f97316'];
            const bgColores = ['#eff6ff','#f5f3ff','#ecfdf5','#fffbeb','#fef2f2','#ecfeff','#fdf2f8','#f0fdfa','#eef2ff','#fff7ed'];

            const filtrados = filtro
                ? productos.filter(p => multiWordMatch(`${p.descripcion || p.nombre || ''} ${p.codigo || ''} ${p.cabys || ''}`, filtro))
                : productos;

            if (!filtrados.length) {
                grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#94a3b8;font-weight:600;"><i class="fas fa-box-open" style="font-size:2rem;display:block;margin-bottom:10px;opacity:0.4;"></i>No hay productos en el inventario</div>';
                return;
            }

            grid.innerHTML = filtrados.map((p, i) => {
                const nombre = p.descripcion || p.nombre || 'Producto';
                const precio = p.precioVenta || p.precio || 0;
                const icono = iconos[i % iconos.length];
                const color = colores[i % colores.length];
                const bg = bgColores[i % bgColores.length];
                return `<div class="product-card" onclick="agregarAlCarrito('${nombre.replace(/'/g,"\\'")}', ${precio})">
                    <div>
                        <div class="product-icon" style="color:${color}; background:${bg};"><i class="${icono}"></i></div>
                        <div class="product-name">${nombre}</div>
                    </div>
                    <div class="product-price">${formatter.format(precio)}</div>
                </div>`;
            }).join('');
        }


        // Búsqueda en tiempo real Premium
        (function() {
            const input = document.getElementById('pos-search-input');
            const dropdown = document.getElementById('pos-search-dropdown');

            function closeDropdown() {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
            }

            input.addEventListener('input', function() {
                const q = this.value.trim().toLowerCase();
                
                // Actualizar grilla visual
                cargarProductos(q);

                if (q.length < 1) {
                    closeDropdown();
                    return;
                }

                const productos = window.muroDB ? window.muroDB.getProductos() : [];
                const matches = productos.filter(p => 
                    multiWordMatch(`${p.descripcion || p.nombre || ''} ${p.codigo || ''} ${p.cabys || ''}`, q)
                ).slice(0, 8);

                dropdown.innerHTML = '';
                if (!matches.length) {
                    dropdown.innerHTML = '<div style="padding:15px; text-align:center; color:#94a3b8; font-size:0.8rem;">No se encontraron productos</div>';
                    dropdown.style.display = 'block';
                    return;
                }

                matches.forEach(p => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `
                        <div class="autocomplete-info">
                            <div class="autocomplete-name">${p.descripcion || p.nombre}</div>
                            <div class="autocomplete-subinfo">
                                <span>SKU: ${p.codigo || '—'}</span>
                                <span style="background:#f1f5f9; padding:2px 6px; border-radius:4px; font-weight:700;">${p.cabys || '00000000'}</span>
                            </div>
                        </div>
                        <div class="autocomplete-price">${formatter.format(p.precioVenta || p.precio || 0)}</div>
                    `;
                    item.onclick = () => {
                        agregarAlCarrito(p.descripcion || p.nombre, p.precioVenta || p.precio || 0);
                        input.value = '';
                        closeDropdown();
                        cargarProductos(''); // Reset grid
                    };
                    dropdown.appendChild(item);
                });
                dropdown.style.display = 'block';
            });

            document.addEventListener('click', closeDropdown);
            input.addEventListener('click', (e) => e.stopPropagation());
        })();


        // Chips de categoría
        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', function() {
                document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                this.classList.add('active');
                const cat = this.textContent.trim();
                if (cat.includes('Favoritos') || cat.includes('Más')) {
                    cargarProductos('');
                } else {
                    cargarProductos(cat);
                }
            });
        });

        function agregarAlCarrito(nombre, precio) {
            const itemExistente = carrito.find(i => i.nombre === nombre);
            if(itemExistente) {
                itemExistente.qty += 1;
            } else {
                carrito.push({ nombre, precio, qty: 1 });
            }
            renderCarrito();
        }

        function cambiarQty(i, delta) {
            carrito[i].qty += delta;
            if(carrito[i].qty <= 0) carrito.splice(i, 1);
            renderCarrito();
        }

        function renderCarrito() {
            const list = document.getElementById('cart-list');
            list.innerHTML = '';
            
            carrito.forEach((item, index) => {
                const totalItem = item.precio * item.qty;
                const el = document.createElement('div');
                el.className = 'cart-item';
                el.innerHTML = `
                    <div class="cart-item-details">
                        <div class="cart-item-name">${item.nombre}</div>
                        <div class="cart-item-price">${formatter.format(item.precio)}</div>
                    </div>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:5px;">
                        <div style="font-weight: 800; color: var(--pos-text);">${formatter.format(totalItem)}</div>
                        <div class="cart-qty-ctrl">
                            <button class="btn-qty" onclick="cambiarQty(${index}, -1)"><i class="fas fa-minus" style="font-size:0.6rem;"></i></button>
                            <span style="font-weight:800; min-width:15px; text-align:center;">${item.qty}</span>
                            <button class="btn-qty" onclick="cambiarQty(${index}, 1)"><i class="fas fa-plus" style="font-size:0.6rem;"></i></button>
                        </div>
                    </div>
                `;
                list.appendChild(el);
            });
            calcularTotal();
        }

        function calcularTotal() {
            const subtotal = carrito.reduce((acc, item) => acc + (item.precio * item.qty), 0);
            const iva = subtotal * 0.13;
            const total = subtotal + iva;

            document.getElementById('txt-subtotal').innerText = formatter.format(subtotal);
            document.getElementById('txt-iva').innerText = formatter.format(iva);
            document.getElementById('txt-total').innerText = formatter.format(total);
            document.getElementById('btn-total').innerText = formatter.format(total);
        }
        
        // Simular inicio con productos reales
        cargarProductos();