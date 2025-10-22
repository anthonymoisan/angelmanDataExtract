# app/v5/public/proxy_auth.py
from __future__ import annotations
import os, json, requests
from configparser import ConfigParser
from requests.auth import HTTPBasicAuth
from flask import Blueprint, request, jsonify
from app.common.security import require_public_app_key

from tools.logger import setup_logger
logger = setup_logger(debug=False)

bp = Blueprint("public_auth", __name__)

# ---- Load server-side .ini ----
_APP_DIR = os.path.dirname(os.path.dirname(__file__))            # src/app/v5
_INI     = os.path.abspath(os.path.join(_APP_DIR, "..", "..", "..", "angelman_viz_keys", "Config5.ini"))

cfg = ConfigParser()
if not cfg.read(_INI):
    raise RuntimeError(f"Config file not found: {_INI}")

# BASIC creds pour l'upstream privé
PROXY_USER = cfg["PROXY_AUTH"]["USER"].strip()
PROXY_PASS = cfg["PROXY_AUTH"]["PASS"].strip()

# Base URL privé (ex: https://…/api/v5)
AUTH_BASE  = cfg["PRIVATE"]["AUTH_BASE_URL"].rstrip("/")

# Header "interne" exigé par require_internal (nom/valeur)
INTERNAL_HEADER_NAME  = (cfg["PRIVATE"].get("INTERNAL_HEADER_NAME")).strip()
INTERNAL_HEADER_VALUE = (cfg["PRIVATE"].get("INTERNAL_HEADER_VALUE")).strip()

LOGIN_URL   = f"{AUTH_BASE}/auth/login"
SECRETQ_URL = f"{AUTH_BASE}/people/secret-question"
VERIFY_URL  = f"{AUTH_BASE}/people/secret-answer/verify"
RESET_URL   = f"{AUTH_BASE}/auth/reset-password"

def _auth():
    return HTTPBasicAuth(PROXY_USER, PROXY_PASS)

def _upstream_headers(extra: dict | None = None) -> dict:
    """
    Construit les entêtes pour l'appel upstream privé :
    - JSON par défaut
    - Header interne exigé par require_internal
    """
    base = {
        "Accept": "application/json",
        INTERNAL_HEADER_NAME: INTERNAL_HEADER_VALUE,
    }
    if extra:
        base.update(extra)
    return base

def _json_or_stub(r: requests.Response) -> tuple[dict, int]:
    try:
        return r.json(), r.status_code
    except ValueError:
        return (
            {
                "upstream_status": r.status_code,
                "upstream_body": (r.text or "")[:400],
            },
            r.status_code,
        )

# --------- PUBLIC: POST /auth/login -----------
@bp.post("/auth/login")
@require_public_app_key
def public_login():
    payload = request.get_json(silent=True) or {}
    # L’upstream privé attend "email" et "password" (cf. v5_auth.auth_login)
    if not payload.get("email") or not payload.get("password"):
        return jsonify({"error": "email et password sont requis"}), 400
    try:
        r = requests.post(
            LOGIN_URL,
            headers=_upstream_headers({"Content-Type": "application/json"}),
            data=json.dumps(payload, ensure_ascii=False),
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy login error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    if r.status_code == 401:
        # Très utile pour diagnostiquer : confirme que le Basic est bien lu côté privé
        logger.warning(
            "proxy_auth: 401 from private on /auth/login (user=%s, basic=%s, internal=%s:%s)",
            PROXY_USER,
            "set" if (PROXY_USER and PROXY_PASS) else "missing",
            INTERNAL_HEADER_NAME,
            INTERNAL_HEADER_VALUE,
        )

    data, code = _json_or_stub(r)
    return jsonify(data), code

# --------- PUBLIC: GET /people/secret-question -----------
@bp.get("/people/secret-question")
@require_public_app_key
def public_secret_question():
    try:
        r = requests.get(
            SECRETQ_URL,
            params=request.args,  # forward all query params
            headers=_upstream_headers(),  # IMPORTANT: header interne ici aussi
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy secret-question error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    data, code = _json_or_stub(r)
    return jsonify(data), code

# --------- PUBLIC: POST /people/secret-answer/verify -----------
@bp.post("/people/secret-answer/verify")
@require_public_app_key
def public_verify_secret_answer():
    payload = request.get_json(silent=True) or {}
    try:
        r = requests.post(
            VERIFY_URL,
            headers=_upstream_headers({"Content-Type": "application/json"}),
            data=json.dumps(payload, ensure_ascii=False),
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy verify-secret-answer error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    data, code = _json_or_stub(r)
    return jsonify(data), code

# --------- PUBLIC: POST /auth/reset-password -----------
@bp.post("/auth/reset-password")
@require_public_app_key
def public_reset_password():
    payload = request.get_json(silent=True) or {}
    try:
        r = requests.post(
            RESET_URL,
            headers=_upstream_headers({"Content-Type": "application/json"}),
            data=json.dumps(payload, ensure_ascii=False),
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy reset-password error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    if r.status_code == 204:
        return ("", 204)
    data, code = _json_or_stub(r)
    return jsonify(data), code
