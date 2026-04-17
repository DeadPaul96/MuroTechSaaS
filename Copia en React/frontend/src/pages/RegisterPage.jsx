import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Building, Store, Desktop, ListOrdered, UserCog, Key, User, Users, AtSign, Phone, ShieldAlt, CheckCircle, ArrowLeft } from 'lucide-react';
import '../styles/register.css';

const RegisterPage = () => {
    const navigate = useNavigate();

    return (
        <main className="reg-body">
            <div className="reg-card">
                <header className="auth-header">
                    <div className="logo-container">
                        <img 
                            src="/imagenes/logo_principal_MUROTECH-removebg-preview.png" 
                            alt="MUROTECH Logo" 
                            style={{ maxHeight: '70px' }}
                        />
                    </div>
                    <p className="subtitle">Registro de Cuenta Profesional v4.4</p>
                </header>

                <form>
                    {/* 1. INFORMACIÓN DEL CONTRIBUYENTE */}
                    <div className="section-box">
                        <div className="section-header">
                            <div className="section-icon"><Building size={24} /></div>
                            <h2 className="section-title">Información del Contribuyente</h2>
                        </div>
                        
                        <div className="grid-2">
                            <div className="input-group">
                                <label className="label-capsule">Tipo de Identificación (v4.4)</label>
                                <select className="premium-select-capsule">
                                    <option value="01">01 - Cédula Física</option>
                                    <option value="02">02 - Cédula Jurídica</option>
                                </select>
                            </div>
                            <div className="input-group">
                                <label className="label-capsule">Número de Identificación</label>
                                <input type="text" className="fi-capsule" placeholder="000000000" />
                            </div>
                        </div>
                    </div>

                    {/* 2. CONFIGURACIÓN TRIBUTARIA */}
                    <div className="section-box">
                        <div className="section-header">
                            <div className="section-icon"><UserCog size={24} /></div>
                            <h2 className="section-title">Configuración Tributaria y API</h2>
                        </div>
                        <div className="grid-3">
                            <div className="input-group">
                                <label className="label-capsule">Sucursal</label>
                                <input type="text" className="fi-capsule" defaultValue="001" />
                            </div>
                            <div className="input-group">
                                <label className="label-capsule">Terminal</label>
                                <input type="text" className="fi-capsule" defaultValue="00001" />
                            </div>
                            <div className="input-group">
                                <label className="label-capsule">Último Consecutivo MH</label>
                                <input type="number" className="fi-capsule" placeholder="Ej: 50" />
                            </div>
                        </div>
                    </div>

                    {/* ACCIONES */}
                    <div className="reg-actions">
                        <Link to="/login" className="back-link">
                            <ArrowLeft size={20} /> Volver al Login
                        </Link>
                        <div className="btn-group">
                            <button type="button" className="btn-progreso">Guardar Progreso</button>
                            <button type="submit" className="btn-finalizar">
                                Finalizar Registro <CheckCircle size={20} style={{ marginLeft: '8px' }} />
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </main>
    );
};

export default RegisterPage;
