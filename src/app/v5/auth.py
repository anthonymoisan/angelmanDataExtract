# app/v5/auth.py
from __future__ import annotations
from flask import Blueprint, jsonify, request, current_app

from sqlalchemy import text
from angelmanSyndromeConnexion.error import (
    AppError, MissingFieldError, ValidationError
)
from angelmanSyndromeConnexion.utils import email_sha256, decrypt_number
from angelmanSyndromeConnexion.peopleRepresentation import (
    updateData, authenticate_and_get_id, verifySecretAnswer
)
from utilsTools import _run_query

from .common import (
    ratelimit, _get_src, _pwd_ok, _normalize_email, _SECRET_QUESTION_LABELS
)

bp = Blueprint("v5_auth", __name__)
from app.v5.common import register_error_handlers; register_error_handlers(bp)

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

        sha = email_sha256(_normalize_email(email))
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
        if not row or row[0][0] is None:
            return jsonify({"ok": False}), 404

        try:
            q_int = int(decrypt_number(row[0][0]))
        except Exception:
            return jsonify({"ok": False}), 500

        label = _SECRET_QUESTION_LABELS.get(q_int, "Question secrète")
        return jsonify({"question": q_int, "label": label}), 200

    except AppError as e:
        # géré par register_error_handlers
        raise e
    except Exception as e:
        current_app.logger.exception("Erreur secret-question")
        return jsonify({"error": f"erreur serveur: {e}"}), 500

@bp.post("/people/secret-answer/verify")
@ratelimit(5)
def api_verify_secret_answer():
    """
    Entrée:
      - email (ou emailAddress) OU id
      - answer (requis)
    Sortie: { "ok": true|false } (toujours 200)
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

        if not answer or (not email and person_id is None):
            return jsonify({"ok": False}), 200

        ok = verifySecretAnswer(email=email if email else None, person_id=person_id, answer=answer)
        return jsonify({"ok": bool(ok)}), 200

    except AppError as e:
        raise e
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

        # vérifie Q/R sans divulguer l'existence du compte
        if not verifySecretAnswer(email=email, person_id=None, answer=answer):
            return jsonify({"ok": False}), 401

        affected = updateData(email_address=email, password=new_pwd)
        return ("", 204) if affected else (jsonify({"ok": False}), 401)

    except AppError as e:
        raise e
    except Exception as e:
        current_app.logger.exception("Erreur reset password")
        return jsonify({"error": f"erreur serveur: {e}"}), 500
