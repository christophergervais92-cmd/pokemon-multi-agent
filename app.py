import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Lazy-loaded real application — no imports needed at detection time
_real_app = None

def _load():
    global _real_app
    if _real_app is None:
        from api.app import create_app
        _real_app = create_app()
    return _real_app


def app(environ, start_response):
    """WSGI entrypoint — loads Flask app on first request."""
    return _load()(environ, start_response)


if __name__ == '__main__':
    _load().run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
