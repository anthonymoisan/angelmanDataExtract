# app/v5/public/proxy_people.py
from __future__ import annotations

import base64
from flask import Blueprint, jsonify, request, Response, abort, current_app

from angelmanSyndromeConnexion.error import (
    AppError,
    MissingFieldError,
    ValidationError,
)
from angelmanSyndromeConnexion.peopleCreate import insertData
from angelmanSyndromeConnexion.peopleRead import (
    giveId,
    fetch_person_decrypted,
    fetch_photo,
    getRecordsPeople,
    identity_public,
    getListPaysTranslate,
)
from angelmanSyndromeConnexion.peopleUpdate import updateData
from angelmanSyndromeConnexion.peopleDelete import deleteDataById

from ..common import _get_src, parse_date_any, register_error_handlers
from app.common.security import require_public_app_key
from PIL import UnidentifiedImageError
from angelmanSyndromeConnexion.utils_image import recompress_image

bp = Blueprint("public_people", __name__)
register_error_handlers(bp)


'''
    Convertisseur d'image nécessaire pour preview heic ou heif
'''
@bp.post("/utils/convert-photo")
@require_public_app_key
def public_convert_photo():
    """
    Reçoit un fichier (multipart) et renvoie un JPEG (bytes) pour preview.
    """
    if "photo" not in request.files:
        return jsonify({"error": "missing photo"}), 400

    f = request.files["photo"]
    blob = f.read()
    if not blob:
        return jsonify({"error": "empty file"}), 400

    try:
        out, mime = recompress_image(blob, target_format="JPEG", quality=85)
        if not out:
            return jsonify({"error": "convert failed"}), 400
        return Response(out, mimetype=mime or "image/jpeg")
    except UnidentifiedImageError as e:
        return jsonify({"error": str(e)}), 415
    except Exception as e:
        return jsonify({"error": f"convert error: {e}"}), 500

# --------------------------------------------------------------------
# Utilitaires locaux (reprise des helpers de app/v5/people.py)
# --------------------------------------------------------------------


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _to_float_or_none(v):
    if v in (None, "", "null"):
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None


def _to_int_or_none(v):
    if v in (None, "", "null"):
        return None
    try:
        return int(str(v).strip())
    except Exception:
        return None


def _payload_people_from_request():
    """
    Retourne (firstname, lastname, email, dob(date), genotype,
              photo_bytes, longC, latC, password, qSec, rSec).
    Supporte multipart/form-data et JSON (photo_base64).
    """
    src = _get_src()

    if request.content_type and request.content_type.startswith("multipart/form-data"):
        form = request.form
        gender = form.get("gender")
        firstname = form.get("firstname")
        lastname = form.get("lastname")
        emailAddress = form.get("emailAddress")
        dob_str = form.get("dateOfBirth")
        genotype = form.get("genotype")
        long = form.get("longitude")
        lat = form.get("latitude")
        password = form.get("password")
        qSec = form.get("qSecrete")
        rSec = form.get("rSecrete")
        file = request.files.get("photo")
        photo_bytes = file.read() if file else None
        is_info = form.get("is_info")
        lang = form.get("lang")
    else:
        data = request.get_json(silent=True) or {}
        gender = data.get("gender")
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        emailAddress = data.get("emailAddress")
        dob_str = data.get("dateOfBirth")
        genotype = data.get("genotype")
        long = data.get("longitude")
        lat = data.get("latitude")
        password = data.get("password")
        qSec = data.get("qSecrete")
        rSec = data.get("rSecrete")
        photo_b64 = data.get("photo_base64")
        is_info = data.get("is_info")
        lang = data.get("lang")
        if photo_b64:
            if "," in photo_b64:
                photo_b64 = photo_b64.split(",", 1)[1]
            photo_bytes = base64.b64decode(photo_b64)
        else:
            photo_bytes = None

    # ✅ check présence avant cast
    if long is None or lat is None:
        raise ValidationError("longitude/latitude requis")


    try:
        longC = float(str(long).replace(",", "."))
        latC = float(str(lat).replace(",", "."))
    except (TypeError, ValueError):
        raise ValidationError("longitude/latitude doivent être numériques")

    if not (-180.0 <= longC <= 180.0):
        raise ValidationError("longitude hors plage [-180, 180]")
    if not (-90.0 <= latC <= 90.0):
        raise ValidationError("latitude hors plage [-90, 90]")

    required = [
        "gender",
        "firstname",
        "lastname",
        "emailAddress",
        "dateOfBirth",
        "genotype",
        "longitude",
        "latitude",
        "password",
        "qSecrete",
        "rSecrete",
        "is_info",
        "lang",
    ]

    def is_missing(v):
        return v is None or (isinstance(v, str) and v.strip() == "")

    # src vient de _get_src() (fusion form/JSON)
    missing = [k for k in required if is_missing(src.get(k))]
    if missing:
        raise MissingFieldError(
            f"Champs manquants: {', '.join(missing)}",
            details={"missing": missing},
        )
    dob = parse_date_any(dob_str)
    return (
        gender,
        firstname,
        lastname,
        emailAddress,
        dob,
        genotype,
        photo_bytes,
        longC,
        latC,
        password,
        qSec,
        rSec,
        is_info,
        lang
    )

# --------------------------------------------------------------------
# Routes PUBLIC -> logique interne (sans HTTP requests)
# --------------------------------------------------------------------


# Update person (JSON ou multipart)
@bp.route("/people/update", methods=["PATCH", "PUT"])
@require_public_app_key
def public_update_person():
    """
    Version publique de /api/v5/people/update :
    - pas de basic auth
    - même logique que api_update_person, mais en direct Python.
    """
    try:
        src = _get_src() or {}
        email_current = (
            (src.get("emailAddress") if isinstance(src, dict) else None)
            or request.args.get("emailAddress")
            or (src.get("email") if isinstance(src, dict) else None)
            or request.args.get("email")
            or ""
        ).strip()
        if not email_current:
            raise MissingFieldError(
                "emailAddress manquant",
                {"missing": ["emailAddress"]},
            )

        kwargs: dict = {}
        for key_src, key_dst in [
            ("firstname", "firstname"),
            ("lastname", "lastname"),
            ("genotype", "genotype"),
            ("city", "city"),
            ("password", "password"),
            ("emailNewAddress", "emailNewAddress"),
            ("newEmail", "emailNewAddress"),
            ("reponseSecrete", "reponseSecrete"),
            ("gender", "gender"),
            ("is_info", "is_info"),

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
        if lon is not None:
            kwargs["longitude"] = lon
        if lat is not None:
            kwargs["latitude"] = lat

        qsec = _to_int_or_none(src.get("questionSecrete"))
        if qsec is not None:
            kwargs["questionSecrete"] = qsec

        if "delete_photo" in src:
            kwargs["delete_photo"] = _to_bool(src.get("delete_photo"))

        if "is_info" in src:
            kwargs["is_info"] = _to_bool(src.get("is_info"))

        photo_bytes = None
        if request.content_type and request.content_type.startswith(
            "multipart/form-data"
        ):
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
            return (
                jsonify(
                    {
                        "ok": True,
                        "updated": 0,
                        "message": "Aucune modification appliquée.",
                    }
                ),
                200,
            )
        return jsonify({"ok": True, "updated": int(affected)}), 200

    except AppError as e:
        # Les AppError sont déjà gérées par register_error_handlers
        raise e
    except Exception as e:
        current_app.logger.exception("Erreur update person (public)")
        return jsonify({"error": f"erreur serveur: {e}"}), 500


# Photo binaire
@bp.get("/people/<int:person_id>/photo")
@require_public_app_key
def public_person_photo(person_id: int):
    photo, mime = fetch_photo(person_id)
    if not photo:
        abort(404)
    return Response(photo, mimetype=mime)


# Info complète (comme /api/v5/people/<id>/info)
@bp.get("/people/<int:person_id>/info")
@require_public_app_key
def public_person_info(person_id: int):
    result = fetch_person_decrypted(person_id)
    return jsonify(result)


# Info publique (comme /api/v5/people/<id>/infoPublic)
@bp.get("/people/<int:person_id>/infoPublic")
@require_public_app_key
def public_person_infoPublic(person_id: int):
    result = identity_public(person_id)
    return jsonify(result)


# Create person (JSON ou multipart)
@bp.post("/people")
@require_public_app_key
def public_create_person():
    try:
        (
            gender,
            fn,
            ln,
            email,
            dob,
            gt,
            photo_bytes,
            long,
            lat,
            password,
            qSec,
            rSec,
            is_info,
            lang,
        ) = _payload_people_from_request()
        new_id = insertData(
            gender,
            fn,
            ln,
            email,
            dob,
            gt,
            photo_bytes,
            long,
            lat,
            password,
            qSec,
            rSec,
            is_info,
            lang,
        )
        return jsonify({"status": "created", "id": new_id}), 200
    except AppError as e:
        return jsonify({"status": "validation error" , "code": e.code,"message": str(e),}), e.http_status
    except Exception:
        current_app.logger.exception("Unhandled error (public_create_person)")
        return (
            jsonify({"status": "error", "message": "Internal server error"}),
            500,
        )


# Delete by id
@bp.delete("/people/delete/<int:person_id>")
@require_public_app_key
def public_delete_person(person_id: int):
    try:
        deleteDataById(person_id)
        return jsonify({"ok": True, "deleted": person_id}), 200
    except AppError as e:
        raise e
    except Exception as e:
        current_app.logger.exception("Erreur suppression par id (public)")
        return jsonify({"error": f"erreur serveur: {e}"}), 500


# Lookup (querystring)
@bp.get("/people/lookup")
@require_public_app_key
def public_lookup_person():
    try:
        email = request.args.get("email") or request.args.get("emailAddress")
        if not email or not email.strip():
            raise MissingFieldError(
                "email (query param) manquant",
                {"missing": ["email"]},
            )
        person_id = giveId(email)
        if person_id is None:
            return jsonify({"status": "Not found"}), 404
        return jsonify({"status": "found", "id": person_id}), 200
    except AppError as e:
        return jsonify({"status": "validation error" , "message" : e.code}), e.http_status
    except Exception:
        current_app.logger.exception("Unhandled error (public_lookup_person)")
        return (
            jsonify({"status": "error", "message": "Internal server error"}),
            500,
        )


# Map People (JSON) — direct DB (getRecordsPeople)
@bp.get("/peopleMapRepresentation")
@require_public_app_key
def public_people_map():
    """
    Version publique de /api/v5/peopleMapRepresentation :
    pas de HTTP interne, on appelle directement getRecordsPeople().
    """
    try:
        df = getRecordsPeople()
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        current_app.logger.exception(
            "[PUBLIC_PROXY][MAP] peopleMapRepresentation ERROR: %s", e
        )
        return jsonify({"error": f"peopleMapRepresentation error: {e}"}), 500

@bp.get("/people/countriesTranslated")
@require_public_app_key
def public_countries_translated():
    """
    Renvoie la liste des pays (code ISO alpha-2 + nom traduit),
    triés alphabétiquement selon la langue demandée.

    Query params:
      - locale (default: fr) ex: fr, en, es, pt_BR
    """
    try:
        locale = request.args.get("locale", "fr").strip()

        # Ex: [{'code': 'BR', 'name': 'Brésil'}, ...]
        countries = getListPaysTranslate(locale=locale) or []

        return jsonify({
            "locale": locale,
            "countries": countries,
            "count": len(countries),
        })

    except Exception as e:
        current_app.logger.exception(
            "[PUBLIC_PROXY][COUNTRIES] countriesTranslated ERROR: %s", e
        )
        return jsonify({
            "error": "countriesTranslated error",
            "detail": str(e),
        }), 500
