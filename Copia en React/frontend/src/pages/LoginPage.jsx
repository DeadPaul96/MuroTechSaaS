import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react';
import '../styles/login.css';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // Simulación de login exitoso
    navigate('/dashboard');
  };

  return (
    <main className="auth-container">
      <div className="auth-card">
        <header className="auth-header">
          <div className="logo-container">
            <img 
              src="/imagenes/logo_principal_MUROTECH-removebg-preview.png" 
              alt="MUROTECH Logo" 
              className="brand-logo"
            />
          </div>
          <p className="subtitle">Plataforma Profesional de Facturación</p>
        </header>

        <form onSubmit={handleSubmit}>
          <div className="input-wrapper">
            <Mail className="input-icon-cap" size={20} />
            <input
              type="email"
              placeholder="Correo electrónico principal"
              className="fi-capsule"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="input-wrapper">
            <Lock className="input-icon-cap" size={20} />
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Contraseña de acceso"
              className="fi-capsule"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="pass-toggle-cap"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>

          <div className="auth-options">
            <label className="remember-me">
              <input type="checkbox" /> Recuérdame
            </label>
            <a href="#" className="forgot-password">¿Olvidaste tu contraseña?</a>
          </div>

          <button type="submit" className="btn-finalizar">
            Iniciar Sesión <ArrowRight size={20} />
          </button>
        </form>

        <footer className="auth-footer">
          <p>
            ¿Nuevo en MUROTECH? <Link to="/registro">Crear cuenta profesional</Link>
          </p>
        </footer>
      </div>
    </main>
  );
};

export default LoginPage;
