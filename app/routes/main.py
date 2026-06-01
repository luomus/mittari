import os
import secrets

from flask import Blueprint, render_template

from app.extensions import cache

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/healthz")
def healthz():
    return "ok", 200


@bp.route("/flush/<flush_secret_key>")
def flush_cache(flush_secret_key: str):
    expected = (os.environ.get("FLUSH_SECRET_KEY") or "").strip()
    if not expected or not secrets.compare_digest(flush_secret_key, expected):
        return "forbidden", 403
    cache.clear()
    return "ok", 200
