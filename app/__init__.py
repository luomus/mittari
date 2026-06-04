import os

from flask import Flask

from app.extensions import cache


def _caching_on() -> bool:
    raw = (os.environ.get("CACHING_ON") or "").strip().lower()
    if not raw:
        return True
    return raw in ("true")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    if _caching_on():
        cache_dir = os.path.join(app.instance_path, "cache")
        os.makedirs(cache_dir, exist_ok=True)
        app.config.setdefault("CACHE_TYPE", "FileSystemCache")
        app.config.setdefault("CACHE_DIR", cache_dir)
    else:
        app.config.setdefault("CACHE_TYPE", "NullCache")
    app.config.setdefault("CACHE_DEFAULT_TIMEOUT", 300)
    cache.init_app(app)

    from app.routes import api_bp, main_bp, stats_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(api_bp)

    return app
