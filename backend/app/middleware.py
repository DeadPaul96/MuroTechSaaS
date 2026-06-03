"""Middleware global: seguridad, CSRF por origen, headers."""
import os

from flask import request, jsonify


def setup_middleware(app):
    """Configura middleware y encabezados de seguridad."""

    @app.before_request
    def validate_origin_on_mutations():
        """CSRF ligero: mutaciones deben venir de orígenes CORS permitidos o llevar Bearer."""
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return None
        if request.path.startswith('/api/seed'):
            return None
        if request.headers.get('Authorization', '').startswith('Bearer '):
            return None
        if request.headers.get('X-CSRF-Token') == os.environ.get('CSRF_SECRET', ''):
            return None
        origin = request.headers.get('Origin') or request.headers.get('Referer', '')
        if not origin:
            return None
        allowed = app.config.get('CORS_ORIGINS') or []
        if not any(origin.startswith(o.rstrip('/')) for o in allowed):
            return jsonify({'message': 'Origen no permitido.', 'code': 'CSRF_ORIGIN'}), 403
        return None

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'geolocation=()')
        response.headers.setdefault('X-XSS-Protection', '1; mode=block')
        if app.config.get('FLASK_ENV') == 'production':
            response.headers.setdefault(
                'Strict-Transport-Security',
                'max-age=31536000; includeSubDomains',
            )
        csp = os.environ.get(
            'CONTENT_SECURITY_POLICY',
            "default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; connect-src 'self' https://api.hacienda.go.cr https://*.onrender.com http://localhost:* http://127.0.0.1:*",
        )
        response.headers.setdefault('Content-Security-Policy', csp)
        if request.path.startswith('/api/'):
            response.headers.setdefault('Cache-Control', 'no-store')
        return response
