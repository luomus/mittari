from app.routes.api import bp as api_bp
from app.routes.main import bp as main_bp
from app.routes.miss import bp as miss_bp
from app.routes.stats import bp as stats_bp

__all__ = ["api_bp", "main_bp", "miss_bp", "stats_bp"]
