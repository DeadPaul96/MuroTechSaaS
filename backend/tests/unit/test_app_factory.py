import pytest

from app import create_app


def test_app_factory_creates_app():
    app = create_app()
    assert app is not None
    assert app.config['SECRET_KEY'] is not None
    assert app.config['SQLALCHEMY_DATABASE_URI']


def test_health_check_endpoint():
    app = create_app()
    client = app.test_client()
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
