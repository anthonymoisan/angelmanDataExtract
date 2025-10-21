# app/common/basic_auth.py
from __future__ import annotations
import os
import base64
from functools import wraps
from flask import request, jsonify
from hmac import compare_digest
from configparser import ConfigParser
from pathlib import Path
import bcrypt

def _load_basic_creds():
    """
    Charge les identifiants:
      - priorité ENV: BASIC_USER / BASIC_PASS_HASH
      - fallback INI: angelman_viz_keys/ConfigAuth.ini [BASIC] USER / PASS_HASH
    NOTE: PASS_HASH est le résultat de bcrypt.hashpw(...).decode()
    """
    user = os.environ.get("BASIC_USER")
    pwd_hash = os.environ.get("BASIC_PASS_HASH")

    if user and pwd_hash:
        return user, pwd_hash

    # fallback INI (au même niveau que 'src/')
    src_dir   = Path(__file__).resolve().parents[2]  # .../src
    proj_root = src_dir.parent
    ini_path  = Path(os.environ.get("AUTH_INI", proj_root / "angelman_viz_keys" / "Config5.ini"))

    cfg = ConfigParser()
    cfg.read(str(ini_path))
    if "BASIC" in cfg:
        u = cfg["BASIC"].get("USER", "")
        ph = cfg["BASIC"].get("PASS_HASH", "")
        return u, ph
    return "", ""

_BASIC_USER, _BASIC_PASS_HASH = _load_basic_creds()

def _parse_basic_header() -> tuple[str | None, str | None]:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("basic "):
        return None, None
    try:
        b64 = auth.split(" ", 1)[1]
        raw = base64.b64decode(b64).decode("utf-8")
        if ":" not in raw:
            return None, None
        u, p = raw.split(":", 1)
        return u, p
    except Exception:
        return None, None

def require_basic(f):
    """
    Décorateur Basic Auth qui compare:
      - username (constant-time compare)
      - password via bcrypt.checkpw (secure)
    Retourne 401 si manquant/incorrect, 503 si non configuré.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not _BASIC_USER or not _BASIC_PASS_HASH:
            return jsonify({"error": "basic auth not configured"}), 503

        u, p = _parse_basic_header()
        if not u or p is None:
            # demande de credential standard pour Basic Auth
            resp = jsonify({"error": "missing basic auth"})
            resp.status_code = 401
            resp.headers["WWW-Authenticate"] = 'Basic realm="Restricted"'
            return resp

        # Compare username en temps constant
        if not compare_digest(u, _BASIC_USER):
            return jsonify({"error": "unauthorized"}), 401

        try:
            # bcrypt requires bytes
            stored_hash = _BASIC_PASS_HASH.encode("utf-8")
            password_bytes = p.encode("utf-8")
            if not bcrypt.checkpw(password_bytes, stored_hash):
                return jsonify({"error": "unauthorized"}), 401
        except Exception:
            # si le hash est corrompu, renvoyer 503 (problème config)
            return jsonify({"error": "basic auth misconfigured"}), 503

        return f(*args, **kwargs)
    return wrapped

def require_internal():
    # OPTIONS: laisser passer les préflights CORS
    if request.method == "OPTIONS":
        return None
    if request.headers.get("X-Internal-Call") != "1":
        return jsonify({"error": "unauthorized"}), 401
    return None