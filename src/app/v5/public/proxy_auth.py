# app/v5/public/proxy_auth.py
from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text

from angelmanSyndromeConnexion.error import AppError, MissingFieldError, ValidationError
from angelmanSyndromeConnexion.peopleUpdate import updateData
from angelmanSyndromeConnexion.peopleAuth import authenticate_and_get_id, verifySecretAnswer, update_person_connection_status
from tools.crypto_utils import email_sha256, decrypt_number
from tools.utilsTools import _run_query

from app.common.security import ratelimit, require_public_app_key
from app.v5.common import _get_src, _pwd_ok, _normalize_email, _SECRET_QUESTION_LABELS

bp = Blueprint("public_auth", __name__)

# --------- PUBLIC: POST /auth/login -----------


@bp.post("/auth/login")
@ratelimit(3)
@require_public_app_key
def public_login():
  """
  Authentification publique :
  - Protégée par X-App-Key (require_public_app_key)
  - Pas de Basic ni d'entête interne
  - Retourne {ok: True, id: ...} ou 401 / 400 / 500
  """
  data = (
      request.get_json(silent=True)
      or request.form.to_dict(flat=True)
      or request.args.to_dict(flat=True)
      or {}
  )

  email = (data.get("email") or "").strip()
  password = data.get("password") or ""

  if not email or not password:
    return jsonify({"error": "email et password sont requis"}), 400

  try:
    person_id = authenticate_and_get_id(email, password, bAngelmanResult=False)
    updated = update_person_connection_status(
            person_id=person_id,
            is_connected=True,
    )

  except Exception:
    current_app.logger.exception("Erreur d'authentification (public_login)")
    return jsonify({"error": "erreur serveur"}), 500

  if person_id is None:
    return jsonify({"ok": False, "message": "identifiants invalides"}), 401

  return jsonify({"ok": True, "id": person_id}), 200

@bp.post("/auth/connection")
@ratelimit(10)
@require_public_app_key
def public_update_person_connection():
    """
    Mise à jour publique du statut de connexion d'une personne.
    - Protégée par X-App-Key
    - Pas de Basic Auth
    - Attend : person_id, is_connected (bool ou 0/1)
    - Retourne {ok: True} ou erreur
    """
    data = (
        request.get_json(silent=True)
        or request.form.to_dict(flat=True)
        or request.args.to_dict(flat=True)
        or {}
    )

    # --- Inputs ---
    person_id = data.get("id")
    is_connected = data.get("is_connected")

    # --- Validation ---
    try:
        person_id = int(person_id)
    except (TypeError, ValueError):
        return jsonify({"error": "person_id invalide"}), 400

    if is_connected in (True, "true", "1", 1):
        is_connected = True
    elif is_connected in (False, "false", "0", 0):
        is_connected = False
    else:
        return jsonify({"error": "is_connected doit être un booléen"}), 400

    # --- Update ---
    try:
        updated = update_person_connection_status(
            person_id=person_id,
            is_connected=is_connected,
        )
    except Exception:
        current_app.logger.exception(
            "[PUBLIC] update_person_connection_status ERROR"
        )
        return jsonify({"error": "erreur serveur"}), 500

    if not updated:
        return jsonify({
            "ok": False,
            "message": "personne introuvable ou inactive"
        }), 404

    return jsonify({
        "ok": True,
        "person_id": person_id,
        "is_connected": is_connected,
    }), 200


# --------- PUBLIC: GET /people/secret-question -----------


@bp.get("/people/secret-question")
@ratelimit(5)
@require_public_app_key
def public_secret_question():
  """
  Expose la question secrète associée à un email.
  Entrée (query ou body): email ou emailAddress
  Sortie:
    - 200 + {question: int, label: str} si ok
    - 404 si pas de question
    - 4xx/5xx si erreur
  """
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
                FROM T_People_Identity
                WHERE email_sha = :sha
                LIMIT 1
            """),
        params={"sha": sha},
        return_result=True,
        bAngelmanResult=False,
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
    # Laisse la gestion aux handlers globaux si tu les utilises
    raise e
  except Exception as e:
    current_app.logger.exception("Erreur public_secret_question")
    return jsonify({"error": f"erreur serveur: {e}"}), 500


# --------- PUBLIC: POST /people/secret-answer/verify -----------


@bp.post("/people/secret-answer/verify")
@ratelimit(5)
@require_public_app_key
def public_verify_secret_answer():
  """
  Vérifie la réponse à la question secrète.
  Entrée (JSON / form / query):
    - email ou emailAddress, ou id
    - answer
  Sortie:
    - 200 + {ok: true/false}
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
    current_app.logger.exception("Erreur public_verify_secret_answer")
    return jsonify({"ok": False}), 200


# --------- PUBLIC: POST /auth/reset-password -----------


@bp.post("/auth/reset-password")
@ratelimit(3)
@require_public_app_key
def public_reset_password():
  """
  Réinitialisation de mot de passe via question secrète.
  Entrée (JSON / form / query via _get_src()):
    - emailAddress (ou email)
    - questionSecrete (1,2,3)
    - reponseSecrete
    - newPassword
  """
  try:
    src = _get_src() or {}
    email = (
        (src.get("emailAddress") if isinstance(src, dict) else None)
        or src.get("email")
        or ""
    ).strip()
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

    # Vérifie la réponse secrète
    if not verifySecretAnswer(email=email, person_id=None, answer=answer):
      return jsonify({"ok": False}), 401

    # Met à jour le mot de passe
    affected = updateData(email_address=email, password=new_pwd)
    return ("", 204) if affected else (jsonify({"ok": False}), 401)

  except AppError as e:
    raise e
  except Exception as e:
    current_app.logger.exception("Erreur public_reset_password")
    return jsonify({"error": f"erreur serveur: {e}"}), 500
