# app/v5/public/proxy_people.py
from __future__ import annotations

import os, json
from configparser import ConfigParser
from functools import wraps
from time import monotonic

import requests
from requests.auth import HTTPBasicAuth
from flask import Blueprint, request, jsonify, Response, current_app

bp = Blueprint("public_people", __name__)

# ----------- Chargement Config (.ini côté serveur) -----------
_APP_DIR  = os.path.dirname(os.path.dirname(__file__))  # -> src/app/v5
_INI_PATH = os.path.abspath(
    os.path.join(_APP_DIR, "..", "..", "..", "angelman_viz_keys", "Config5.ini")
)

_cfg = ConfigParser()
if not _cfg.read(_INI_PATH):
    raise RuntimeError(f"Config file not found: {_INI_PATH}")

try:
    # Identifiants du proxy (EN CLAIR, distincts du hash utilisé côté privé)
    PROXY_USER = _cfg["PROXY_AUTH"]["USER"].strip()
    PROXY_PASS = _cfg["PROXY_AUTH"]["PASS"].strip()
    # Base privée pour tous les endpoints /api/v5
    PRIVATE_BASE = _cfg["PRIVATE"]["PEOPLE_BASE_URL"].rstrip("/")
    POINTS_URL = f"{PRIVATE_BASE}/pointRemarquableRepresentation"
    PEOPLE_URL = f"{PRIVATE_BASE}/peopleMapRepresentation"
except KeyError as e:
    raise RuntimeError(f"Config5.ini missing key: {e}")

if not PROXY_USER or not PROXY_PASS or not PRIVATE_BASE:
    raise RuntimeError("Config5.ini incomplete: PROXY_AUTH.USER, PROXY_AUTH.PASS, PRIVATE.AUTH_BASE_URL requis")


# ------------------------ Petit rate-limit IP ------------------------
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


# ------------------------ Utilitaires proxy ------------------------
TIMEOUT = (6, 25)  # (connect, read)

def _forward_json(method: str, path: str, *, params=None, payload=None):
    """Forward JSON -> JSON."""
    url = f"{PRIVATE_BASE}{path}"
    try:
        r = requests.request(
            method,
            url,
            params=params,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            data=json.dumps(payload or {}, ensure_ascii=False),
            timeout=TIMEOUT,
            auth=HTTPBasicAuth(PROXY_USER, PROXY_PASS),
        )
    except requests.RequestException as e:
        current_app.logger.exception("Proxy error JSON %s %s", method, url)
        return jsonify({"error": f"proxy error: {e}"}), 502

    # essaie de renvoyer du JSON, sinon un aperçu texte
    try:
        data = r.json()
        return jsonify(data), r.status_code
    except ValueError:
        return jsonify(
            {"upstream_status": r.status_code, "upstream_body": (r.text or "")[:600]}
        ), r.status_code


def _forward_multipart(method: str, path: str):
    """Forward multipart/form-data en préservant fichiers et champs."""
    url = f"{PRIVATE_BASE}{path}"

    # Champs simples
    form = {}
    for k, v in request.form.items():
        form[k] = v

    # Fichiers
    files = {}
    for name, storage in request.files.items():
        # (filename, fileobj, content_type)
        files[name] = (storage.filename, storage.stream, storage.content_type)

    try:
        r = requests.request(
            method,
            url,
            params=request.args,
            data=form,
            files=files,
            timeout=TIMEOUT,
            auth=HTTPBasicAuth(PROXY_USER, PROXY_PASS),
        )
    except requests.RequestException as e:
        current_app.logger.exception("Proxy error multipart %s %s", method, url)
        return jsonify({"error": f"proxy error: {e}"}), 502

    # Si le backend renvoie JSON, on le passe tel quel; sinon texte
    ctype = r.headers.get("Content-Type", "")
    if "application/json" in ctype:
        try:
            return jsonify(r.json()), r.status_code
        except ValueError:
            pass
    return jsonify(
        {"upstream_status": r.status_code, "upstream_body": (r.text or "")[:600]}
    ), r.status_code


def _forward_binary(method: str, path: str, *, params=None):
    """Forward binaire (photo)."""
    url = f"{PRIVATE_BASE}{path}"
    try:
        r = requests.request(
            method,
            url,
            params=params,
            stream=True,
            timeout=TIMEOUT,
            auth=HTTPBasicAuth(PROXY_USER, PROXY_PASS),
        )
    except requests.RequestException as e:
        current_app.logger.exception("Proxy error binary %s %s", method, url)
        return jsonify({"error": f"proxy error: {e}"}), 502

    # Passe le flux binaire et le mimetype d'origine
    return Response(
        r.content,
        status=r.status_code,
        mimetype=r.headers.get("Content-Type", "application/octet-stream"),
    )


# ------------------------ Routes PUBLIC -> PRIVATE ------------------------

# Update person (JSON ou multipart)
@bp.route("/people/update", methods=["PATCH", "PUT"])
@ratelimit(3)
def public_update_person():
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        return _forward_multipart(request.method, "/people/update")
    # JSON fallback
    payload = request.get_json(silent=True) or {}
    return _forward_json(request.method, "/people/update", params=request.args, payload=payload)


# Photo binaire
@bp.get("/people/<int:person_id>/photo")
def public_person_photo(person_id: int):
    return _forward_binary("GET", f"/people/{person_id}/photo")


# Info (JSON)
@bp.get("/people/<int:person_id>/info")
def public_person_info(person_id: int):
    return _forward_json("GET", f"/people/{person_id}/info", params=request.args)

# Info (JSON)
@bp.get("/people/<int:person_id>/infoPublic")
def public_person_infoPublic(person_id: int):
    return _forward_json("GET", f"/people/{person_id}/infoPublic", params=request.args)


# Create person (JSON ou multipart)
@bp.post("/people")
def public_create_person():
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        return _forward_multipart("POST", "/people")
    payload = request.get_json(silent=True) or {}
    return _forward_json("POST", "/people", params=request.args, payload=payload)


# Delete by id
@bp.delete("/people/delete/<int:person_id>")
@ratelimit(3)
def public_delete_person(person_id: int):
    return _forward_json("DELETE", f"/people/delete/{person_id}", params=request.args)


# Lookup (querystring)
@bp.get("/people/lookup")
def public_lookup_person():
    return _forward_json("GET", "/people/lookup", params=request.args)


# Map People (JSON)
@bp.get("/peopleMapRepresentation")
def public_people_map():
    return _forward_json("GET", "/peopleMapRepresentation", params=request.args)


# Point Remarquable - création (JSON)
@bp.post("/pointRemarquable")
def public_create_point_remarquable():
    payload = request.get_json(silent=True) or {}
    return _forward_json("POST", "/pointRemarquable", params=request.args, payload=payload)


# Point Remarquable - liste (JSON)
@bp.get("/pointRemarquableRepresentation")
def public_point_remarquable_representation():
    return _forward_json("GET", "/pointRemarquableRepresentation", params=request.args)
