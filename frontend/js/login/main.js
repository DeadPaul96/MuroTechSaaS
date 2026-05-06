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
    const btn = document.getElementById('loginBtn');
    
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

            // Efecto de carga
            if (btn) {
                btn.classList.add('loading');
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Autenticando...';
            }

            // Llamada real al API de Login usando CONFIG
            fetch(`${CONFIG.API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            })
            .then(res => res.json())
            .then(data => {
                if (data.token) {
                    // Guardar sesión real
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    localStorage.setItem('accesos', JSON.stringify(data.accesos));
                    
                    // Alerta de éxito
                    Swal.fire({
                        icon: 'success',
                        title: '¡Bienvenido!',
                        text: `Hola de nuevo, ${data.user.nombre}`,
                        timer: 1500,
                        showConfirmButton: false
                    }).then(() => {
                        window.location.href = 'panelControl.html';
                    });
                } else {
                    if (btn) {
                        btn.classList.remove('loading');
                        btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Iniciar Sesión';
                    }
                    showLoginError(data.message || 'Error al iniciar sesión');
                }
            })
            .catch(err => {
                if (btn) {
                    btn.classList.remove('loading');
                    btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Iniciar Sesión';
                }
                showLoginError('Error de conexión con el servidor.');
                console.error(err);
            });
        });
    }
});
