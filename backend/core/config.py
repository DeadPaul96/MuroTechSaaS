"""Configuración centralizada — delega a app.config.Config."""
# La configuración principal está en app/config.py
# Este módulo se mantiene solo para compatibilidad con scripts existentes.
from app.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig

__all__ = ['Config', 'DevelopmentConfig', 'TestingConfig', 'ProductionConfig']
