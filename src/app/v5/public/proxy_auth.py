# app/v5/public/proxy_auth.py
from __future__ import annotations
import os, json, requests
from configparser import ConfigParser
from requests.auth import HTTPBasicAuth
from flask import Blueprint, request, jsonify

from tools.logger import setup_logger
logger = setup_logger(debug=False)

bp = Blueprint("public_auth", __name__)

# ---- Load server-side .ini ----
_APP_DIR = os.path.dirname(os.path.dirname(__file__))            # src/app/v5
_INI     = os.path.abspath(os.path.join(_APP_DIR, "..", "..", "..", "angelman_viz_keys", "Config5.ini"))

cfg = ConfigParser()
if not cfg.read(_INI):
    raise RuntimeError(f"Config file not found: {_INI}")

# For the proxy we need BASIC creds in **clear**
PROXY_USER = cfg["PROXY_AUTH"]["USER"].strip()
PROXY_PASS = cfg["PROXY_AUTH"]["PASS"].strip()
AUTH_BASE  = cfg["PRIVATE"]["AUTH_BASE_URL"].rstrip("/")

LOGIN_URL   = f"{AUTH_BASE}/auth/login"
SECRETQ_URL = f"{AUTH_BASE}/people/secret-question"
VERIFY_URL  = f"{AUTH_BASE}/people/secret-answer/verify"
RESET_URL   = f"{AUTH_BASE}/auth/reset-password"

def _auth():
    return HTTPBasicAuth(PROXY_USER, PROXY_PASS)

# --------- PUBLIC: POST /auth/login -----------
@bp.post("/auth/login")
def public_login():
    payload = request.get_json(silent=True) or {}
    if not payload.get("email") or not payload.get("password"):
        return jsonify({"error": "email et password sont requis"}), 400
    try:
        r = requests.post(
            LOGIN_URL,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            data=json.dumps(payload, ensure_ascii=False),
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy login error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    try:
        data = r.json()
    except ValueError:
        data = {"upstream_status": r.status_code, "upstream_body": (r.text or "")[:400]}

    if r.status_code == 401:
        logger.warning("proxy_auth: 401 from private. user=%s pass_len=%d url=%s",
                       PROXY_USER, len(PROXY_PASS), LOGIN_URL)
    return jsonify(data), r.status_code

# --------- PUBLIC: GET /people/secret-question -----------
@bp.get("/people/secret-question")
def public_secret_question():
    # Relay query string (?email=... or emailAddress=...)
    try:
        r = requests.get(
            SECRETQ_URL,
            params=request.args,  # forward all query params
            headers={"Accept": "application/json"},
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy secret-question error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    try:
        data = r.json()
    except ValueError:
        data = {"upstream_status": r.status_code, "upstream_body": (r.text or "")[:400]}
    return jsonify(data), r.status_code

# --------- PUBLIC: POST /people/secret-answer/verify -----------
@bp.post("/people/secret-answer/verify")
def public_verify_secret_answer():
    # Private endpoint accepts JSON or query; we forward JSON body
    payload = request.get_json(silent=True) or {}
    try:
        r = requests.post(
            VERIFY_URL,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            data=json.dumps(payload, ensure_ascii=False),
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy verify-secret-answer error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    try:
        data = r.json()
    except ValueError:
        data = {"upstream_status": r.status_code, "upstream_body": (r.text or "")[:400]}
    return jsonify(data), r.status_code

# --------- PUBLIC: POST /auth/reset-password -----------
@bp.post("/auth/reset-password")
def public_reset_password():
    payload = request.get_json(silent=True) or {}
    try:
        r = requests.post(
            RESET_URL,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            data=json.dumps(payload, ensure_ascii=False),
            timeout=(6, 15),
            auth=_auth(),
        )
    except requests.RequestException as e:
        logger.exception("proxy reset-password error")
        return jsonify({"error": f"proxy error: {e}"}), 502

    # This private route may return 204 (no body)
    if r.status_code == 204:
        return ("", 204)
    try:
        data = r.json()
    except ValueError:
        data = {"upstream_status": r.status_code, "upstream_body": (r.text or "")[:400]}
    return jsonify(data), r.status_code
