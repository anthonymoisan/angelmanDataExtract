# app/v5/mail.py
from __future__ import annotations
import os, ssl
from configparser import ConfigParser
from email.message import EmailMessage
from flask import Blueprint, jsonify, request, current_app

from .common import sanitize_subject, sanitize_body
from app.common.security import ratelimit

bp = Blueprint("v5_mail", __name__)
from .common import register_error_handlers; register_error_handlers(bp)
from app.common.basic_auth import require_basic

# Chargement Config5.ini (même logique qu'avant)
_app_dir = os.path.dirname(os.path.dirname(__file__))  # -> src/app
_cfg = ConfigParser()
_cfg.read(os.path.abspath(os.path.join(_app_dir, "..", "..", "angelman_viz_keys", "Config5.ini")))
SMTP_HOST = _cfg["SMTP_HOST"]["SMTP"]
SMTP_PORT = int(_cfg["SMTP_PORT"]["PORT"])  # 465 ou 587
SMTP_USER = _cfg["SMTP_USER"]["USER"]
SMTP_PASS = _cfg["SMTP_PASS"]["PASS"]
MAIL_TO   = "contact@fastfrance.org"
MAIL_FROM = "asconnect@fastfrance.org"

@bp.post("/contact")
@ratelimit(5)
@require_basic
def relay_contact():
    data = request.get_json(force=True, silent=True) or {}
    subject = sanitize_subject(data.get("subject", ""))
    body    = sanitize_body(data.get("body", ""))

    # CAPTCHA token "<timestamp_ms>:<a>x<b>" + answer
    captcha_token = (data.get("captcha_token") or "").strip()
    captcha_answer = data.get("captcha_answer")
    try:
        ts_str, ab = captcha_token.split(":")
        a_str, b_str = ab.split("x")
        a = int(a_str); b = int(b_str)
        client = int(captcha_answer)
        if a + b != client:
            return jsonify({"error": "captcha invalide"}), 400
        from datetime import datetime, timezone
        ts_ms = int(ts_str)
        age_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - ts_ms
        if age_ms > 5 * 60 * 1000:
            return jsonify({"error": "captcha expiré"}), 400
    except Exception:
        return jsonify({"error": "captcha manquant/incorrect"}), 400

    if not subject or not body:
        return jsonify({"error": "subject et body requis"}), 400

    try:
        port = int(SMTP_PORT)
    except Exception:
        return jsonify({"error": "SMTP_PORT invalide"}), 500
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return jsonify({"error": "SMTP non configuré côté serveur"}), 500

    msg = EmailMessage()
    msg["Subject"] = subject if subject.startswith("AS Connect - ") else f"AS Connect - {subject}"
    msg["From"] = SMTP_USER
    msg["Reply-To"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.set_content(body)

    try:
        import smtplib
        if port == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, port, context=ssl.create_default_context(), timeout=12) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, port, timeout=12) as s:
                s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
    except Exception as e:
        current_app.logger.exception("Erreur SMTP (OVH)")
        return jsonify({"error": f"envoi impossible: {e}"}), 502

    return jsonify({"ok": True})
