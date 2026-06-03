from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_migrate import Migrate
import os

# Initialize database, migration tool, CORS, and rate limiter globally
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()

_default_limits = os.environ.get('RATELIMIT_DEFAULT', '300 per day;60 per hour').split(';')
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URL') or os.environ.get('REDIS_URL', 'memory://'),
    default_limits=[lim.strip() for lim in _default_limits if lim.strip()],
)
