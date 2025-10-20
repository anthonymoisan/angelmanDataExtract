# app/v5/public/proxy_mail.py
from __future__ import annotations
import json, os
from configparser import ConfigParser
from functools import wraps
from time import monotonic
import requests
from requests.auth import HTTPBasicAuth
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint("public_mail", __name__)

_APP_DIR = os.path.dirname(os.path.dirname(__file__))  # -> src/app/v5
_INI_PATH = os.path.abspath(os.path.join(_APP_DIR, '..', '..', '..', 'angelman_viz_keys', 'Config5.ini'))

_cfg = ConfigParser()
if not _cfg.read(_INI_PATH):
    raise RuntimeError(f"Config file not found: {_INI_PATH}")

try:
    # <-- IMPORTANT : on lit le user/pass EN CLAIR pour le proxy
    PROXY_USER = _cfg["PROXY_AUTH"]["USER"].strip()
    PROXY_PASS = _cfg["PROXY_AUTH"]["PASS"].strip()
    PRIVATE_CONTACT_URL = _cfg["PRIVATE"]["CONTACT_URL"].strip()
except KeyError as e:
    raise RuntimeError(f"Config5.ini missing key: {e}")

if not PROXY_USER or not PROXY_PASS or not PRIVATE_CONTACT_URL:
    raise RuntimeError("Config5.ini incomplete: PROXY_AUTH.USER, PROXY_AUTH.PASS, PRIVATE.CONTACT_URL required")

_last_hit: dict[str, float] = {}
def ratelimit(seconds: float = 5.0):
    def deco(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "anon"
            now = monotonic()
            if now - _last_hit.get(ip, 0.0) < seconds:
                return jsonify({"error": "Trop de requêtes, réessaie dans quelques secondes."}), 429
            _last_hit[ip] = now
            return f(*args, **kwargs)
        return wrapped
    return deco

@bp.post("/contact")
@ratelimit(5)
def relay_contact_public():
    payload = request.get_json(force=True, silent=True) or {}

    # petite validation
    subject = (payload.get("subject") or "").strip()
    body    = (payload.get("body") or "").strip()
    if not subject or not body:
        return jsonify({"error": "subject et body requis"}), 400

    try:
        resp = requests.post(
            PRIVATE_CONTACT_URL,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
            data=json.dumps(payload, ensure_ascii=False),
            timeout=(6, 15),
            auth=HTTPBasicAuth(PROXY_USER, PROXY_PASS),  # <<< mot de passe en clair
        )
    except requests.exceptions.Timeout:
        return jsonify({"error": "Délai dépassé côté serveur"}), 504
    except requests.exceptions.SSLError as e:
        current_app.logger.exception("SSL error vers PRIVATE_CONTACT_URL")
        return jsonify({"error": f"Erreur SSL: {e}"}), 502
    except requests.RequestException as e:
        current_app.logger.exception("Erreur de proxy vers PRIVATE_CONTACT_URL")
        return jsonify({"error": f"Proxy en échec: {e}"}), 502

    try:
        data = resp.json()
    except ValueError:
        data = {"upstream_status": resp.status_code, "upstream_body": (resp.text or "")[:512]}
    return jsonify(data), resp.status_code
