# app/v5/common.py
from __future__ import annotations
import re
from datetime import date, datetime
from functools import wraps
from time import monotonic

from flask import jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy.exc import IntegrityError

from angelmanSyndromeConnexion.error import (
    AppError, DuplicateEmailError
)

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

# ---------- Helpers requêtes / validations ----------
MAX_SUBJECT = 140
MAX_BODY    = 5000

def sanitize_subject(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r'[\r\n]+', ' ', s)[:MAX_SUBJECT]

def sanitize_body(s: str) -> str:
    return (s or "").strip()[:MAX_BODY]

def _get_src():
    # multipart => request.form ; sinon JSON
    ctype = (request.content_type or "")
    if ctype.startswith("multipart/form-data"):
        return request.form
    return request.get_json(silent=True) or {}

def parse_date_any(s: str) -> date:
    s = (s or "").strip()
    # ISO YYYY-MM-DD (ou datetime ISO)
    try:
        return date.fromisoformat(s.split("T")[0].split(" ")[0])
    except Exception:
        pass
    # DD/MM/YYYY
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        pass
    # MM/DD/YYYY
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except Exception:
        pass
    raise ValueError("dateOfBirth invalide. Formats acceptés: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, DD/MM/YYYY, MM/DD/YYYY")

def _pwd_ok(p: str) -> bool:
    if not isinstance(p, str): return False
    p = p.strip()
    if len(p) < 8: return False
    if not any(c.isupper() for c in p): return False
    specials = r'!@#$%^&*(),.?":{}|<>_-+=~;\/[]'
    return any(c in specials for c in p)

def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()

_SECRET_QUESTION_LABELS = {
    1: "Nom de naissance de votre maman ?",
    2: "Nom de votre acteur de cinéma favori ?",
    3: "Nom de votre animal de compagnie favori ?",
}

# ---------- Handlers d'erreurs pour un blueprint ----------
def register_error_handlers(bp):
    @bp.app_errorhandler(AppError)
    def _handle_app_error(e: AppError):
        resp = {"status": "error", "code": e.code, "message": str(e)}
        if getattr(e, "details", None):
            resp["details"] = e.details
        return jsonify(resp), e.http_status

    @bp.app_errorhandler(IntegrityError)
    def _handle_integrity(e: IntegrityError):
        # MySQL duplicate unique key -> 1062
        if "1062" in str(getattr(e, "orig", e)):
            err = DuplicateEmailError("Un enregistrement avec cet email existe déjà")
            return _handle_app_error(err)
        return jsonify({"status":"error","code":"db_integrity","message":"Violation d'intégrité"}), 409

    @bp.app_errorhandler(RequestEntityTooLarge)
    def _handle_too_large(e: RequestEntityTooLarge):
        return jsonify({"status":"error","code":"payload_too_large","message":"Fichier trop volumineux (>4 MiB)"}), 413
