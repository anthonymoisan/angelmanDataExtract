# app/debug_routes.py
import os, hmac
from flask import Blueprint, current_app, jsonify, request, Response

bp = Blueprint("debug_routes", __name__)

def _bool_env(name: str, default: bool=False) -> bool:
    return os.getenv(name, "true" if default else "false").lower() in ("1","true","yes","on")

def _token_ok() -> bool:
    """Autorise si ROUTES_TOKEN défini et correspond, sinon refuse en prod."""
    token_cfg = os.getenv("ROUTES_TOKEN", "").strip()
    # Cherche le jeton dans le header ou en query string
    provided = (request.headers.get("X-Admin-Token") or
                request.args.get("token") or "").strip()
    if token_cfg:
        return bool(provided) and hmac.compare_digest(provided, token_cfg)
    # Si aucun token configuré: seulement autoriser en local (EXPOSE_ROUTES_LOCAL=true)
    return _bool_env("EXPOSE_ROUTES_LOCAL", False)

@bp.before_request
def _guard():
    if not _token_ok():
        # 401 et en-tête WWW-Authenticate pour signaler une auth requise
        return Response("Unauthorized", 401, {
            "WWW-Authenticate": 'Bearer realm="routes"',
            "Cache-Control": "no-store"
        })

@bp.get("/_routes")
def list_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        methods = sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS"))
        routes.append({
            "rule": str(rule),
            "endpoint": rule.endpoint,
            "methods": methods,
        })
    return jsonify(routes)
