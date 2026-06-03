document.addEventListener('DOMContentLoaded', async () => {
    const pending = JSON.parse(localStorage.getItem('pending_registration') || 'null');
    const plansGrid = document.getElementById('plansGrid');
    const planNote = document.getElementById('planNote');

    // Temporalmente comentado para permitir acceso a la pantalla
    // if (!pending || !pending.empresa_id) {
    //     Swal.fire({
    //         icon: 'warning',
    //         title: 'Registro incompleto',
    //         text: 'No se encontró información de registro. Por favor complete el formulario de registro primero.',
    //         confirmButtonText: 'Ir al registro'
    //     }).then(() => window.location.href = 'registro.html');
    //     return;
    // }

    planNote.innerHTML = pending ? `Bienvenido ${pending.nombre || 'Usuario'}. Seleccione un plan y complete el pago demo para activar su cuenta.` : 'Seleccione un plan para ver los detalles.';

    const alertError = (message) => Swal.fire('Error', message, 'error');

    async function fetchPlanes() {
        try {
            const res = await fetch('/api/planes');
            if (!res.ok) throw new Error('No se pudieron cargar los planes.');
            const data = await res.json();
            return data.plans || [];
        } catch (err) {
            // Si la API no está disponible, mostrar planes de ejemplo
            console.log('API no disponible, usando planes de ejemplo');
            return [
                {
                    tipo: 'basico',
                    label: 'Plan Básico',
                    amount: 15000,
                    description: 'Ideal para pequeñas empresas',
                    plan_cuota: 50
                },
                {
                    tipo: 'emisor',
                    label: 'Plan Emisor',
                    amount: 35000,
                    description: 'Para empresas en crecimiento',
                    plan_cuota: 200
                },
                {
                    tipo: 'premium',
                    label: 'Plan Premium',
                    amount: 65000,
                    description: 'Para grandes volúmenes',
                    plan_cuota: 500
                },
                {
                    tipo: 'enterprise',
                    label: 'Plan Enterprise',
                    amount: 120000,
                    description: 'Solución personalizada',
                    plan_cuota: 1000
                }
            ];
        }
    }

    function renderPlan(plan) {
        const card = document.createElement('div');
        card.className = 'plan' + (plan.tipo === 'emisor' ? ' plan-popular' : '');

        const badge = document.createElement('div');
        badge.className = 'plan-badge';
        badge.textContent = plan.label.toUpperCase();
        card.appendChild(badge);

        const title = document.createElement('h3');
        title.textContent = plan.label;
        card.appendChild(title);

        const price = document.createElement('p');
        price.className = 'price';
        price.innerHTML = `₡${Number(plan.amount).toLocaleString('es-CR')} <span class="period">/mes</span>`;
        card.appendChild(price);

        const description = document.createElement('p');
        description.style.margin = '0';
        description.style.color = '#475569';
        description.textContent = plan.description;
        card.appendChild(description);

        const list = document.createElement('ul');
        list.style.listStyle = 'none';
        list.style.paddingLeft = '0';
        list.style.margin = '14px 0 0 0';
        list.innerHTML = `
            <li><i class="fas fa-check"></i> Hasta ${plan.plan_cuota} facturas activas</li>
            <li><i class="fas fa-check"></i> Pago mensual en colones</li>
            <li><i class="fas fa-check"></i> Activación instantánea tras pago</li>
        `;
        card.appendChild(list);

        const btn = document.createElement('button');
        btn.className = 'btn-choose';
        btn.dataset.plan = plan.tipo;
        btn.textContent = 'Seleccionar';
        btn.onclick = () => selectPlan(plan);
        card.appendChild(btn);

        return card;
    }

    async function selectPlan(plan) {
        const nombre = pending?.nombre || 'Nuevo Usuario';
        const empresaId = pending?.empresa_id || null;

        const result = await Swal.fire({
            title: '',
            showClass: { popup: 'animate__animated animate__fadeInUp animate__faster' },
            customClass: {
                popup: 'premium-swal-popup',
                confirmButton: 'btn-confirm-premium',
                cancelButton: 'btn-cancel-premium'
            },
            width: 520,
            html: `
                <div class="payment-modal">
                    <div class="pm-header">
                        <div class="pm-icon"><i class="fas fa-credit-card"></i></div>
                        <div class="pm-header-text">
                            <h4>Checkout — ${plan.label}</h4>
                            <p>Pago seguro para activar tu suscripción</p>
                        </div>
                    </div>

                    <div class="pm-summary">
                        <div class="pm-summary-row">
                            <span class="pm-summary-label">Plan</span>
                            <span class="pm-summary-value">${plan.label}</span>
                        </div>
                        <div class="pm-summary-row">
                            <span class="pm-summary-label">Cuota incluida</span>
                            <span class="pm-summary-value">${plan.plan_cuota} facturas</span>
                        </div>
                        <div class="pm-summary-row">
                            <span class="pm-summary-label">Ciclo de facturación</span>
                            <span class="pm-summary-value">Mensual</span>
                        </div>
                        <div class="pm-summary-row pm-summary-total">
                            <span class="pm-summary-label">Total a pagar</span>
                            <span class="pm-summary-value">₡${Number(plan.amount).toLocaleString('es-CR')}</span>
                        </div>
                    </div>

                    <div class="pm-card-form">
                        <div class="pm-field-group">
                            <label class="pm-field-label">Nombre en la tarjeta</label>
                            <input id="card-name" class="pm-input" placeholder="JUAN PÉREZ" autocomplete="cc-name">
                        </div>
                        <div class="pm-field-group">
                            <label class="pm-field-label">Número de tarjeta</label>
                            <input id="card-number" class="pm-input" placeholder="4242 4242 4242 4242" autocomplete="cc-number" maxlength="19">
                        </div>
                        <div class="pm-row">
                            <div class="pm-field-group">
                                <label class="pm-field-label">Vencimiento</label>
                                <input id="card-exp" class="pm-input" placeholder="MM/AA" autocomplete="cc-exp" maxlength="5">
                            </div>
                            <div class="pm-field-group">
                                <label class="pm-field-label">CVC</label>
                                <input id="card-cvc" class="pm-input" placeholder="123" autocomplete="cc-csc" maxlength="4">
                            </div>
                        </div>
                    </div>

                    <div class="pm-secure">
                        <i class="fas fa-lock"></i> Pago simulado — entorno de demostración seguro
                    </div>
                </div>
            `,
            focusConfirm: false,
            showCancelButton: true,
            confirmButtonText: '<i class="fas fa-shield-alt" style="margin-right:8px"></i> Confirmar pago',
            cancelButtonText: 'Cancelar',
            preConfirm: () => {
                const name = document.getElementById('card-name').value.trim();
                const number = document.getElementById('card-number').value.trim();
                const exp = document.getElementById('card-exp').value.trim();
                const cvc = document.getElementById('card-cvc').value.trim();
                if (!name || !number || !exp || !cvc) {
                    Swal.showValidationMessage('Complete todos los campos de la tarjeta.');
                    return false;
                }
                return { name, number, exp, cvc };
            },
            didOpen: () => {
                const cardNum = document.getElementById('card-number');
                const cardExp = document.getElementById('card-exp');

                if (cardNum) {
                    cardNum.addEventListener('input', (e) => {
                        let v = e.target.value.replace(/\D/g, '').substring(0, 16);
                        e.target.value = v.replace(/(.{4})/g, '$1 ').trim();
                    });
                }
                if (cardExp) {
                    cardExp.addEventListener('input', (e) => {
                        let v = e.target.value.replace(/\D/g, '').substring(0, 4);
                        if (v.length >= 3) v = v.substring(0, 2) + '/' + v.substring(2);
                        e.target.value = v;
                    });
                }
            }
        });

        if (!result.isConfirmed || !result.value) {
            return;
        }

        Swal.fire({ title: 'Procesando pago...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

        try {
            let paymentId = pending?.payment_id || null;
            let paymentCreated = false;

            if (!paymentId || pending?.plan_tipo !== plan.tipo) {
                if (!empresaId) {
                    throw new Error('No se encontró información de registro. Por favor complete el registro primero.');
                }

                const checkoutRes = await fetch('/api/pagos/checkout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ empresa_id: empresaId, plan_tipo: plan.tipo })
                });

                const checkoutData = await checkoutRes.json();
                if (!checkoutRes.ok) throw new Error(checkoutData.message || 'Error creando la orden de pago.');
                paymentId = checkoutData.payment_id;
                paymentCreated = true;
            }

            const confirmRes = await fetch('/api/pagos/confirmar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ payment_id: paymentId, provider: 'demo', transaction_id: `DEMO-${Date.now()}` })
            });
            const confirmData = await confirmRes.json();
            if (!confirmRes.ok) throw new Error(confirmData.message || 'Error confirmando el pago.');

            Swal.fire({ icon: 'success', title: 'Pago confirmado', text: `Su plan ${plan.label} se activó correctamente.` })
                .then(() => {
                    localStorage.removeItem('pending_registration');
                    window.location.href = 'inicioSesion.html';
                });
        } catch (error) {
            Swal.fire('Error', error.message || 'No se pudo completar el pago.', 'error');
        }
    }

    const plans = await fetchPlanes();
    if (!plans.length) return;

    plans.forEach(plan => {
        plansGrid.appendChild(renderPlan(plan));
    });
});
