def register_blueprints(app):
    """Registra los blueprints del backend."""
    from .public import bp as public_bp
    from .auth import bp as auth_bp
    from .companies import bp as companies_bp
    from .invoices import bp as invoices_bp
    from .customers import bp as customers_bp
    from .products import bp as products_bp
    from .reports import bp as reports_bp
    from .audit import bp as audit_bp
    from .superadmin import bp as superadmin_bp
    from .payments import bp as payments_bp
    from .config import bp as config_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(superadmin_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(config_bp)
