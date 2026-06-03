from app.extensions import limiter


def rate_limited(limit):
    def decorator(f):
        return limiter.limit(limit)(f)
    return decorator
