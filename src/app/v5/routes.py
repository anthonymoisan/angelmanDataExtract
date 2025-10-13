# app/v5/routes.py
from __future__ import annotations

import base64
import os
import re
import ssl
from datetime import date, datetime, timezone
from email.message import EmailMessage
from functools import wraps
from time import monotonic

from flask import jsonify, request, Response, abort, current_app
from werkzeug.exceptions import RequestEntityTooLarge

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

# Outils communs / accès DB
from utilsTools import _run_query

# Modules métier existants
from angelmanSyndromeConnexion.peopleRepresentation import (
    verifySecretAnswer,
    deleteDataById,
    updateData,
    getRecordsPeople,
    giveId,
    fetch_photo,
    fetch_person_decrypted,
    insertData,
    authenticate_and_get_id,
)
from angelmanSyndromeConnexion.pointRemarquable import (
    getRecordsPointsRemarquables,
    insertPointRemarquable,
)
from angelmanSyndromeConnexion.error import (
    AppError,
    MissingFieldError,
    DuplicateEmailError,
    ValidationError,
)
from angelmanSyndromeConnexion.utils import (
    email_sha256,
    decrypt_number,
    decrypt_bytes_to_str_strict,
)

from flask import Blueprint

bp = Blueprint("v5", __name__)

# ------------------------- Config SMTP (depuis angelman_viz_keys/Config5.ini) -------------------------
from configparser import ConfigParser

_app_dir = os.path.dirname(os.path.dirname(__file__))  # -> src/app
_cfg = ConfigParser()
_cfg.read(os.path.abspath(os.path.join(_app_dir, "..", "..", "angelman_viz_keys", "Config5.ini")))
SMTP_HOST = _cfg["SMTP_HOST"]["SMTP"]
SMTP_PORT = int(_cfg["SMTP_PORT"]["PORT"])  # 465 ou 587
SMTP_USER = _cfg["SMTP_USER"]["USER"]
SMTP_PASS = _cfg["SMTP_PASS"]["PASS"]
MAIL_TO   = "contact@fastfrance.org"
MAIL_FROM = "asconnect@fastfrance.org"

# ------------------------- Gestion erreurs -------------------------
@bp.app_errorhandler(AppError)
def handle_app_error(e: AppError):
    resp = {"status": "error", "code": e.code, "message": str(e)}
    if getattr(e, "details", None):
        resp["details"] = e.details
    return jsonify(resp), e.http_status

@bp.app_errorhandler(IntegrityError)
def handle_integrity(e: IntegrityError):
    # MySQL duplicate unique key -> 1062
    if "1062" in str(getattr(e, "orig", e)):
        err = DuplicateEmailError("Un enregistrement avec cet email existe déjà")
        return handle_app_error(err)
    return jsonify({"status": "error", "code": "db_integrity", "message": "Violation d'intégrité"}), 409

@bp.app_errorhandler(RequestEntityTooLarge)
def handle_too_large(e: RequestEntityTooLarge):
    return jsonify({"status": "error", "code": "payload_too_large", "message": "Fichier trop volumineux (>4 MiB)"}), 413

# ------------------------- Rate limit & helpers -------------------------
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

MAX_SUBJECT = 140
MAX_BODY    = 5000

def sanitize_subject(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r'[\r\n]+', ' ', s)[:MAX_SUBJECT]

def sanitize_body(s: str) -> str:
    return (s or "").strip()[:MAX_BODY]

_SECRET_QUESTION_LABELS = {
    1: "Nom de naissance de votre maman ?",
    2: "Nom de votre acteur de cinéma favori ?",
    3: "Nom de votre animal de compagnie favori ?",
}

def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()

# Unifie la source ; multipart => request.form ; sinon JSON
def _get_src():
    ctype = (request.content_type or "")
    if ctype.startswith("multipart/form-data"):
        return request.form
    return request.get_json(silent=True) or {}

# Parseur de dates souple
def parse_date_any(s: str) -> date:
    s = (s or "").strip()
    try:
        return date.fromisoformat(s.split("T")[0].split(" ")[0])
    except Exception:
        pass
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        pass
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except Exception:
        pass
    raise ValueError("dateOfBirth invalide. Formats acceptés: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, DD/MM/YYYY, MM/DD/YYYY")

# Mot de passe : règles minimales
def _pwd_ok(p: str) -> bool:
    if not isinstance(p, str):
        return False
    p = p.strip()
    if len(p) < 8:
        return False
    if not any(c.isupper() for c in p):
        return False
    specials = r'!@#$%^&*(),.?":{}|<>_-+=~;\/[]'
    return any(c in specials for c in p)

# ------------------------- Endpoints v5 -------------------------

@bp.post("/contact")
@ratelimit(5)
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
        ts_ms = int(ts_str)
        age_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - ts_ms
        if age_ms > 5 * 60 * 1000:
            return jsonify({"error": "captcha expiré"}), 400
    except Exception:
        return jsonify({"error": "captcha manquant/incorrect"}), 400

    if not subject or not body:
        return jsonify({"error": "subject et body requis"}), 400

    # Envoi SMTP
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

@bp.route("/people/update", methods=["PATCH", "PUT"])
@ratelimit(3)
def api_update_person():
    try:
        def _to_bool(v):
            if isinstance(v, bool): return v
            if isinstance(v, (int, float)): return v != 0
            if isinstance(v, str): return v.strip().lower() in {"1","true","yes","on"}
            return False
        def _to_float_or_none(v):
            if v in (None, "", "null"): return None
            try: return float(str(v).replace(",", "."))
            except: return None
        def _to_int_or_none(v):
            if v in (None, "", "null"): return None
            try: return int(str(v).strip())
            except: return None

        src = _get_src() or {}
        email_current = (
            (src.get("emailAddress") if isinstance(src, dict) else None)
            or request.args.get("emailAddress")
            or (src.get("email") if isinstance(src, dict) else None)
            or request.args.get("email")
            or ""
        ).strip()
        if not email_current:
            raise MissingFieldError("emailAddress manquant", {"missing": ["emailAddress"]})

        kwargs = {}
        for key_src, key_dst in [
            ("firstname", "firstname"),
            ("lastname", "lastname"),
            ("genotype", "genotype"),
            ("city", "city"),
            ("password", "password"),
            ("emailNewAddress", "emailNewAddress"),
            ("newEmail", "emailNewAddress"),
            ("reponseSecrete", "reponseSecrete"),
        ]:
            val = src.get(key_src)
            if isinstance(val, str):
                val = val.strip()
            if val not in (None, ""):
                kwargs[key_dst] = val

        if src.get("dateOfBirth"):
            kwargs["dateOfBirth"] = parse_date_any(src.get("dateOfBirth"))

        lon = _to_float_or_none(src.get("longitude"))
        lat = _to_float_or_none(src.get("latitude"))
        if lon is not None: kwargs["longitude"] = lon
        if lat is not None: kwargs["latitude"] = lat

        qsec = _to_int_or_none(src.get("questionSecrete"))
        if qsec is not None:
            kwargs["questionSecrete"] = qsec

        if "delete_photo" in src:
            kwargs["delete_photo"] = _to_bool(src.get("delete_photo"))

        photo_bytes = None
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            f = request.files.get("photo")
            if f and f.filename:
                photo_bytes = f.read()
        else:
            b64 = src.get("photo_base64")
            if b64:
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                photo_bytes = base64.b64decode(b64)
        if photo_bytes is not None:
            kwargs["photo"] = photo_bytes

        affected = updateData(email_address=email_current, **kwargs)
        if affected == 0:
            return jsonify({"ok": True, "updated": 0, "message": "Aucune modification appliquée."}), 200
        return jsonify({"ok": True, "updated": int(affected)}), 200

    except AppError as e:
        return handle_app_error(e)
    except Exception as e:
        current_app.logger.exception("Erreur update person")
        return jsonify({"error": f"erreur serveur: {e}"}), 500

@bp.get("/people/secret-question")
@ratelimit(5)
def api_get_secret_question():
    try:
        src = _get_src() or {}
        email = (
            request.args.get("email")
            or request.args.get("emailAddress")
            or (src.get("email") if isinstance(src, dict) else None)
            or (src.get("emailAddress") if isinstance(src, dict) else None)
            or ""
        ).strip()
        if not email:
            raise MissingFieldError("email manquant", {"missing": ["email"]})

        email_norm = _normalize_email(email)
        sha = email_sha256(email_norm)
        row = _run_query(
            text("""
                SELECT secret_question
                FROM T_ASPeople
                WHERE email_sha = :sha
                LIMIT 1
            """),
            params={"sha": sha},
            return_result=True,
        )
        if not row:
            return jsonify({"ok": False}), 404

        enc_q = row[0][0]
        if enc_q is None:
            return jsonify({"ok": False}), 404

        try:
            q_val = decrypt_number(enc_q)
            q_int = int(q_val)
        except Exception:
            return jsonify({"ok": False}), 500

        label = _SECRET_QUESTION_LABELS.get(q_int, "Question secrète")
        return jsonify({"question": q_int, "label": label}), 200

    except AppError as e:
        return handle_app_error(e)
    except Exception as e:
        current_app.logger.exception("Erreur secret-question")
        return jsonify({"error": f"erreur serveur: {e}"}), 500

@bp.post("/people/secret-answer/verify")
@ratelimit(5)
def api_verify_secret_answer():
    """
    Entrée (JSON/form/query):
      - email (ou emailAddress) OU id
      - answer (requis)
    Sortie: { "ok": true|false } (toujours 200, pas d'info de présence compte)
    """
    try:
        src = _get_src() or {}
        email = (src.get("email") or request.args.get("email") or "").strip()
        if not email:
            email = (src.get("emailAddress") or request.args.get("emailAddress") or "").strip()

        id_raw = src.get("id") or request.args.get("id")
        try:
            person_id = int(id_raw) if id_raw not in (None, "", "null") else None
        except Exception:
            person_id = None

        answer = (src.get("answer") or request.args.get("answer") or "").strip()
        if not answer:
            return jsonify({"ok": False}), 200
        if not email and person_id is None:
            return jsonify({"ok": False}), 200

        ok = verifySecretAnswer(email=email if email else None, person_id=person_id, answer=answer)
        return jsonify({"ok": bool(ok)}), 200

    except AppError as e:
        return handle_app_error(e)
    except Exception:
        current_app.logger.exception("Erreur verify secret answer")
        return jsonify({"ok": False}), 200

@bp.post("/auth/reset-password")
@ratelimit(3)
def api_reset_password():
    try:
        src = _get_src() or {}
        email = ((src.get("emailAddress") if isinstance(src, dict) else None) or src.get("email") or "").strip()
        if not email:
            raise MissingFieldError("emailAddress manquant", {"missing": ["emailAddress"]})

        q_raw = src.get("questionSecrete")
        try:
            question = int(str(q_raw).strip())
        except Exception:
            raise ValidationError("questionSecrete doit être un entier 1..3")
        if question not in (1, 2, 3):
            raise ValidationError("questionSecrete doit être 1, 2 ou 3")

        answer = src.get("reponseSecrete")
        if not isinstance(answer, str) or not answer.strip():
            raise MissingFieldError("reponseSecrete manquante ou vide", {"missing": ["reponseSecrete"]})

        new_pwd = src.get("newPassword")
        if not isinstance(new_pwd, str) or not new_pwd.strip():
            raise MissingFieldError("newPassword manquant", {"missing": ["newPassword"]})
        if not _pwd_ok(new_pwd):
            return jsonify({
                "ok": False,
                "code": "weak_password",
                "message": "Mot de passe trop faible (≥8 caractères, ≥1 majuscule, ≥1 caractère spécial).",
            }), 400

        # Vérifie Q/R secrètes sans divulguer l'existence du compte
        if not verifySecretAnswer(email=email, person_id=None, answer=answer):
            return jsonify({"ok": False}), 401

        affected = updateData(email_address=email, password=new_pwd)
        if affected:
            return ("", 204)
        else:
            return jsonify({"ok": False}), 401

    except AppError as e:
        return handle_app_error(e)
    except Exception as e:
        current_app.logger.exception("Erreur reset password")
        return jsonify({"error": f"erreur serveur: {e}"}), 500

@bp.get("/people/<int:person_id>/photo")
def person_photo(person_id: int):
    photo, mime = fetch_photo(person_id)
    if not photo:
        abort(404)
    return Response(photo, mimetype=mime)

@bp.get("/people/<int:person_id>/info")
def person_info(person_id: int):
    result = fetch_person_decrypted(person_id)
    return jsonify(result)

@bp.post("/auth/login")
def auth_login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        data = request.form.to_dict(flat=True)
    if not data:
        data = request.args.to_dict(flat=True)

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email et password sont requis"}), 400

    try:
        person_id = authenticate_and_get_id(email, password)
    except Exception:
        current_app.logger.exception("Erreur d'authentification")
        return jsonify({"error": "erreur serveur"}), 500

    if person_id is None:
        return jsonify({"ok": False, "message": "identifiants invalides"}), 401
    return jsonify({"ok": True, "id": person_id}), 200

@bp.delete("/people/delete/<int:person_id>")
@ratelimit(3)
def api_delete_person_by_id(person_id: int):
    try:
        deleteDataById(person_id)
        return jsonify({"ok": True, "deleted": person_id}), 200
    except AppError as e:
        return handle_app_error(e)
    except Exception as e:
        current_app.logger.exception("Erreur suppression par id")
        return jsonify({"error": f"erreur serveur: {e}"}), 500

@bp.get("/peopleMapRepresentation")
def peopleMapRepresentation():
    df = getRecordsPeople()
    return jsonify(df.to_dict(orient="records"))

@bp.get("/pointRemarquableRepresentation")
def pointRemarquableRepresentation():
    df = getRecordsPointsRemarquables()
    return jsonify(df.to_dict(orient="records"))

def get_payloadPeople_from_request():
    """
    Retourne (firstname, lastname, email, dob(date), genotype, photo_bytes, longC, latC, password, qSec, rSec).
    Supporte multipart/form-data et JSON (photo_base64).
    """
    src = _get_src()
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        form = request.form
        firstname    = form.get("firstname")
        lastname     = form.get("lastname")
        emailAddress = form.get("emailAddress")
        dob_str      = form.get("dateOfBirth")
        genotype     = form.get("genotype")
        long         = form.get("longitude")
        lat          = form.get("latitude")
        password     = form.get("password")
        qSec         = form.get("qSecrete")
        rSec         = form.get("rSecrete")
        file = request.files.get("photo")
        photo_bytes = file.read() if file else None
    else:
        data = request.get_json(silent=True) or {}
        firstname    = data.get("firstname")
        lastname     = data.get("lastname")
        emailAddress = data.get("emailAddress")
        dob_str      = data.get("dateOfBirth")
        genotype     = data.get("genotype")
        long         = data.get("longitude")
        lat          = data.get("latitude")
        password     = data.get("password")
        qSec         = data.get("qSecrete")
        rSec         = data.get("rSecrete")
        photo_b64    = data.get("photo_base64")
        if photo_b64:
            if "," in photo_b64:
                photo_b64 = photo_b64.split(",", 1)[1]
            photo_bytes = base64.b64decode(photo_b64)
        else:
            photo_bytes = None

    try:
        longC = float(str(long).replace(",", "."))
        latC = float(str(lat).replace(",", "."))
    except ValueError:
        raise ValidationError("longitude/latitude doivent être numériques")

    if not (-180.0 <= longC <= 180.0):
        raise ValidationError("longitude hors plage [-180, 180]")
    if not (-90.0 <= latC <= 90.0):
        raise ValidationError("latitude hors plage [-90, 90]")

    required = [
        "firstname","lastname","emailAddress","dateOfBirth","genotype",
        "longitude","latitude","password","qSecrete","rSecrete",
    ]
    def is_missing(v): return v is None or (isinstance(v, str) and v.strip() == "")
    missing = [k for k in required if is_missing(src.get(k))]
    if missing:
        raise MissingFieldError(
            f"Champs manquants: {', '.join(missing)}",
            details={"missing": missing},
        )

    dob = parse_date_any(dob_str)
    return firstname, lastname, emailAddress, dob, genotype, photo_bytes, longC, latC, password, qSec, rSec

@bp.post("/people")
def create_person():
    try:
        fn, ln, email, dob, gt, photo_bytes, long, lat, password, qSec, rSec = get_payloadPeople_from_request()
        new_id = insertData(fn, ln, email, dob, gt, photo_bytes, long, lat, password, qSec, rSec)
        return jsonify({"status": "created", "id": new_id}), 201
    except AppError as e:
        return jsonify({"status": e.http_status, "message": e.code}), e.http_status
    except Exception:
        current_app.logger.exception("Unhandled error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

def get_payloadPointRemarquable_from_request():
    """
    Retourne (longitude, latitude, short_desc, long_desc).
    Supporte JSON et form-data.
    """
    src = _get_src()
    raw_lon = src.get("longitude") or src.get("lon")
    raw_lat = src.get("latitude")  or src.get("lat")
    short_desc = src.get("short_desc") or src.get("short") or src.get("title")
    long_desc  = src.get("long_desc")  or src.get("description") or ""

    missing = []
    def _miss(v): return v is None or (isinstance(v, str) and v.strip() == "")
    if _miss(raw_lon):     missing.append("longitude")
    if _miss(raw_lat):     missing.append("latitude")
    if _miss(short_desc):  missing.append("short_desc")
    if missing:
        raise MissingFieldError(
            f"Champs manquants: {', '.join(missing)}",
            details={"missing": missing},
        )

    try:
        lon = float(str(raw_lon).replace(",", "."))
        lat = float(str(raw_lat).replace(",", "."))
    except ValueError:
        raise ValidationError("longitude/latitude doivent être numériques")

    if not (-180.0 <= lon <= 180.0):
        raise ValidationError("longitude hors plage [-180, 180]")
    if not (-90.0 <= lat <= 90.0):
        raise ValidationError("latitude hors plage [-90, 90]")

    sd = str(short_desc).strip()
    ld = str(long_desc).strip()
    return lon, lat, sd, ld

@bp.post("/pointRemarquable")
def create_pointRemarquable():
    try:
        longitude, latitude, short_desc, long_desc = get_payloadPointRemarquable_from_request()
        new_id = insertPointRemarquable(longitude, latitude, short_desc, long_desc)
        resp = jsonify({"status": "created", "id": new_id})
        resp.status_code = 201
        resp.headers["Location"] = f"/api/v5/pointRemarquable/{new_id}"
        return resp
    except AppError as e:
        return jsonify({"status": e.http_status, "message": e.code}), e.http_status
    except Exception:
        current_app.logger.exception("Unhandled error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@bp.get("/people/lookup")
def get_idPerson():
    try:
        email = request.args.get("email") or request.args.get("emailAddress")
        if not email or not email.strip():
            raise MissingFieldError("email (query param) manquant", {"missing": ["email"]})

        person_id = giveId(email)
        if person_id is None:
            return jsonify({"status": "not_found"}), 404
        else:
            return jsonify({"status": "found", "id": person_id}), 200
    except AppError as e:
        return jsonify({"status": e.http_status, "message": e.code}), e.http_status
    except Exception:
        current_app.logger.exception("Unhandled error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
