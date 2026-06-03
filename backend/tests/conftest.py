import os

import sys



import pytest



sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



from cryptography.fernet import Fernet



os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only-32bytes!!')

os.environ.setdefault('ENCRYPTION_KEY', Fernet.generate_key().decode())

os.environ.setdefault('FLASK_ENV', 'testing')

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CSRF_SECRET', 'test-csrf-secret')





@pytest.fixture(scope='session')

def app():

    from app import create_app

    flask_app = create_app('testing')

    flask_app.config['TESTING'] = True

    with flask_app.app_context():

        yield flask_app





@pytest.fixture

def client(app):

    return app.test_client()


