function showLoginError(msg) {
    let el = document.getElementById('login-error');
    if (!el) {
        el = document.createElement('div');
        el.id = 'login-error';
        el.style.cssText = 'background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;border-radius:10px;padding:10px 14px;font-size:0.85rem;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;';
        const form = document.getElementById('loginForm');
        form.insertBefore(el, form.firstChild);
    }
    el.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + msg;
}


/**
 * Inicializa los controladores de eventos para la pantalla de login.
 */
function initLoginHandlers() {
    // Toggle de visibilidad de contraseña
    const passwordInput = document.getElementById('password');
    const passwordToggle = document.getElementById('passwordToggle');

    if (passwordInput && passwordToggle) {
        passwordToggle.addEventListener('click', () => {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Actualizar icono
            const icon = passwordToggle.querySelector('i');
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');
        });
    }

    // Placeholder para olvidé mi contraseña
    const forgotLink = document.querySelector('.forgot-password');
    if (forgotLink) {
        forgotLink.addEventListener('click', (e) => {
            e.preventDefault();
            Swal.fire({
                title: 'Recuperación de Contraseña',
                text: 'Funcionalidad de recuperación en desarrollo. Por favor, contacte a soporte@murotech.cr.',
                icon: 'info',
                confirmButtonColor: '#1e40af'
            });
        });
    }
}

/*
  =============================================================
  INICIALIZADOR PRINCIPAL
  =============================================================
*/
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar manejadores específicos de login
    initLoginHandlers();

    // Lógica de Submit del Formulario
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const rememberMe = document.getElementById('rememberMe').checked;

            if (!email || !password) {
                showLoginError('Por favor, complete todos los campos.');
                return;
            }

            // Credenciales demo para presentación al cliente
            const DEMO_USERS = [
                { email: 'admin@murotech.cr',   password: 'Admin123', nombre: 'Administrador' },
                { email: 'demo@murotech.cr',     password: 'Demo123',  nombre: 'Usuario Demo'  },
                { email: 'factura@murotech.cr',  password: 'Factura1', nombre: 'Facturador'    }
            ];

            const btn = document.getElementById('loginBtn');
            btn.classList.add('loading');
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verificando...';

            setTimeout(() => {
                const user = DEMO_USERS.find(u => u.email === email && u.password === password);

                if (!user) {
                    btn.classList.remove('loading');
                    btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Iniciar Sesión';
                    showLoginError('Credenciales incorrectas. Usa: admin@murotech.cr / Admin123');
                    return;
                }

                localStorage.setItem('murotech_session', JSON.stringify({
                    user: user.email,
                    nombre: user.nombre,
                    active: true,
                    remember: rememberMe,
                    timestamp: new Date().getTime()
                }));

                irA('panelControl.html');
            }, 1200);
        });
    }
});
