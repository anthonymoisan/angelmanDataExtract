#from datetime import date, datetime
from functools import wraps
from time import monotonic
from flask import jsonify,request
from configparser import ConfigParser
import os

# ---------- Rate limit ----------
_last_hit: dict[str, float] = {}
def ratelimit(seconds: float = 5.0):
    def deco(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "anon"
            now = monotonic()
            last = _last_hit.get(ip, 0.0)
            if now - last < seconds:
                return jsonify({"error": "Trop de requêtes, réessaie dans quelques secondes."}), 429
            _last_hit[ip] = now
            return f(*args, **kwargs)
        return wrapped
    return deco

_cfg = ConfigParser()
_cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "angelman_viz_keys", "Config5.ini")))
_PUBLIC_KEY = (_cfg.get("PUBLIC", "APP_KEY", fallback="") or "").strip()

def require_public_app_key(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not _PUBLIC_KEY:  # Si non configuré, refuse (ou laisse passer selon ta politique)
            return jsonify({"error":"public key not configured"}), 503
        key = request.headers.get("X-App-Key", "")
        if key != _PUBLIC_KEY:
            return jsonify({"error":"forbidden"}), 403
        return f(*args, **kwargs)
    return wrapped
