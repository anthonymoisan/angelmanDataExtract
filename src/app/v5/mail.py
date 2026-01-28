# app/v5/mail.py
from __future__ import annotations

import os
import ssl
from configparser import ConfigParser
from email.message import EmailMessage
from email.utils import parseaddr

from flask import Blueprint, jsonify, request, current_app

from .common import sanitize_subject, sanitize_body, register_error_handlers
from app.common.security import ratelimit
from app.common.basic_auth import require_basic, require_internal

bp = Blueprint("v5_mail", __name__)
bp.before_request(require_internal)
register_error_handlers(bp)

# -------------------------------------------------------------------
# Chargement Config5.ini (même logique qu'avant)
# -------------------------------------------------------------------
_app_dir = os.path.dirname(os.path.dirname(__file__))  # -> src/app
_cfg = ConfigParser()
_cfg.read(os.path.abspath(os.path.join(_app_dir, "..", "..", "angelman_viz_keys", "Config5.ini")))

SMTP_HOST = _cfg["SMTP_HOST"]["SMTP"]
SMTP_PORT = int(_cfg["SMTP_PORT"]["PORT"])  # 465 ou 587
SMTP_USER = _cfg["SMTP_USER"]["USER"]
SMTP_PASS = _cfg["SMTP_PASS"]["PASS"]

MAIL_TO = "contact@angelmananalytics.org"

# Fallback Reply-To si aucun mail_from fourni (ou invalide)
MAIL_FROM_DEFAULT = "asconnect@fastfrance.org"


def sanitize_email(value: str) -> str:
    """Retourne un email normalisé ou '' si invalide."""
    if not value:
        return ""
    _, email = parseaddr(str(value).strip())
    email = (email or "").strip().lower()

    # Anti header injection + validation basique
    if "@" not in email or any(c in email for c in ("\r", "\n")):
        return ""
    return email


@bp.post("/contact")
@ratelimit(5)
@require_basic
def relay_contact():
    data = request.get_json(force=True, silent=True) or {}

    subject = sanitize_subject(data.get("subject", ""))
    body = sanitize_body(data.get("body", ""))

    # ---------------------------------------------------------------
    # mail_from paramétrique (utilisé en Reply-To)
    # ---------------------------------------------------------------
    mail_from_param = sanitize_email(data.get("mail_from", ""))
    reply_to = mail_from_param or MAIL_FROM_DEFAULT

    # (Optionnel) rendre visible dans le corps si fourni
    if mail_from_param:
        body = f"Message de : {mail_from_param}\n\n{body}"

    # ---------------------------------------------------------------
    # CAPTCHA token "<timestamp_ms>:<a>x<b>" + answer
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

    # ---------------------------------------------------------------
    # Construction du mail
    # ---------------------------------------------------------------
    msg = EmailMessage()
    msg["Subject"] = subject if subject.startswith("AS Connect - ") else f"AS Connect - {subject}"

    # Important : garder From fixe (SMTP) pour SPF/DKIM/délivrabilité
    msg["From"] = SMTP_USER
    msg["Reply-To"] = reply_to

    msg["To"] = MAIL_TO
    msg.set_content(body)

    # ---------------------------------------------------------------
    # Envoi SMTP OVH
    # ---------------------------------------------------------------
    try:
        import smtplib

        if port == 465:
            with smtplib.SMTP_SSL(
                SMTP_HOST,
                port,
                context=ssl.create_default_context(),
                timeout=12
            ) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, port, timeout=12) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)

    except Exception as e:
        current_app.logger.exception("Erreur SMTP (OVH)")
        return jsonify({"error": f"envoi impossible: {e}"}), 502

    return jsonify({"ok": True})
