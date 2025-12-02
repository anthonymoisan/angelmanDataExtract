# app/v5/public/proxy_mail.py
from __future__ import annotations
import os, ssl, json
from configparser import ConfigParser
from email.message import EmailMessage
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, current_app

from app.common.security import ratelimit, require_public_app_key
from app.v5.common import sanitize_subject, sanitize_body

bp = Blueprint("public_mail", __name__)

# -------------------------------------------------------------------
# Charger la même config que le mail privé
# -------------------------------------------------------------------

_APP_DIR = os.path.dirname(os.path.dirname(__file__))  # -> src/app/v5
_INI_PATH = os.path.abspath(
    os.path.join(_APP_DIR, "..", "..", "..", "angelman_viz_keys", "Config5.ini")
)

_cfg = ConfigParser()
if not _cfg.read(_INI_PATH):
    raise RuntimeError(f"Config file not found: {_INI_PATH}")

SMTP_HOST = _cfg["SMTP_HOST"]["SMTP"]
SMTP_PORT = int(_cfg["SMTP_PORT"]["PORT"])
SMTP_USER = _cfg["SMTP_USER"]["USER"]
SMTP_PASS = _cfg["SMTP_PASS"]["PASS"]

MAIL_TO   = "contact@fastfrance.org"
MAIL_FROM = "asconnect@fastfrance.org"


# -------------------------------------------------------------------
#  ROUTE PUBLIQUE : /api/public/contact
#  → mêmes validations que le endpoint privé
#  → même SMTP local
#  → sans proxy, sans requests
# -------------------------------------------------------------------

@bp.post("/contact")
@ratelimit(5)         # 5 requêtes / min
@require_public_app_key
def relay_contact_public():
    # On lit le body brut (pour fallback éventuel)
    raw_body = request.get_data(cache=False)

    # 1) Tentative standard Flask
    data = None
    try:
        data = request.get_json(silent=True, force=False)
    except Exception:
        # On log juste en debug si tu veux, mais pas verbeux
        current_app.logger.debug("PUBLIC CONTACT: get_json() a levé une exception", exc_info=True)

    # 2) Si pas de dict, on tente à la main avec json.loads
    if not isinstance(data, dict):
        try:
            text = raw_body.decode("utf-8", errors="replace")
            data = json.loads(text)
        except Exception:
            current_app.logger.warning("PUBLIC CONTACT: JSON invalide ou manquant")
            return jsonify({"error": "JSON invalide côté serveur"}), 400

    # À partir d'ici, data est un dict
    subject = sanitize_subject(data.get("subject", ""))
    body    = sanitize_body(data.get("body", ""))

    # ---------------------------------------------------------------
    # CAPTCHA (copié du endpoint privé)
    # ---------------------------------------------------------------
    captcha_token = (data.get("captcha_token") or "").strip()
    captcha_answer = data.get("captcha_answer")

    try:
        ts_str, ab = captcha_token.split(":")
        a_str, b_str = ab.split("x")
        a = int(a_str)
        b = int(b_str)
        client = int(captcha_answer)

        if a + b != client:
            return jsonify({"error": "captcha invalide"}), 400

        ts_ms = int(ts_str)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        if now_ms - ts_ms > 5 * 60 * 1000:
            return jsonify({"error": "captcha expiré"}), 400

    except Exception:
        return jsonify({"error": "captcha manquant/incorrect"}), 400

    # ---------------------------------------------------------------
    # Champs obligatoires
    # ---------------------------------------------------------------
    if not subject or not body:
        return jsonify({"error": "subject et body requis"}), 400

    # ---------------------------------------------------------------
    # Vérification config SMTP
    # ---------------------------------------------------------------
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return jsonify({"error": "SMTP non configuré côté serveur"}), 500

    # ---------------------------------------------------------------
    # Construction du mail
    # ---------------------------------------------------------------
    msg = EmailMessage()
    msg["Subject"] = (
        subject if subject.startswith("AS Connect - ")
        else f"AS Connect - {subject}"
    )
    msg["From"] = SMTP_USER
    msg["Reply-To"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.set_content(body)

    # ---------------------------------------------------------------
    # Envoi SMTP OVH (comme le endpoint privé)
    # ---------------------------------------------------------------
    try:
        import smtplib

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                SMTP_HOST,
                SMTP_PORT,
                timeout=12,
                context=ssl.create_default_context()
            ) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)

    except Exception as e:
        current_app.logger.exception("Erreur SMTP (public_mail)")
        return jsonify({"error": f"envoi impossible: {e}"}), 502

    return jsonify({"ok": True}), 200
