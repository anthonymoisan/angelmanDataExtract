#from datetime import date, datetime
from functools import wraps
from time import monotonic
from flask import jsonify,request

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