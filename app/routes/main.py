import hashlib
import os
import secrets

from flask import Blueprint, current_app, render_template

from app.extensions import cache

# Matches cachelib.file.FileSystemCache internal filenames
_FS_COUNT_FILE_HASH = hashlib.md5(b"__wz_cache_count").hexdigest()
_FS_TX_SUFFIX = ".__wz_cache"


def _count_filesystem_cache_entries(cache_dir: str) -> int:
    if not cache_dir or not os.path.isdir(cache_dir):
        return 0
    n = 0
    for name in os.listdir(cache_dir):
        if name == _FS_COUNT_FILE_HASH or name.endswith(_FS_TX_SUFFIX):
            continue
        if os.path.isfile(os.path.join(cache_dir, name)):
            n += 1
    return n

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
    cache_dir = current_app.config.get("CACHE_DIR", "")
    removed = _count_filesystem_cache_entries(cache_dir)
    cache.clear()
    return f"ok: removed {removed} cache entries\n", 200, {"Content-Type": "text/plain; charset=utf-8"}
