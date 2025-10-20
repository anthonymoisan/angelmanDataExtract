# app/v5/people.py
from __future__ import annotations
import base64
from flask import Blueprint, jsonify, request, Response, abort, current_app

from angelmanSyndromeConnexion.error import (
    AppError, MissingFieldError, ValidationError
)
from angelmanSyndromeConnexion.peopleCreate import insertData
from angelmanSyndromeConnexion.peopleRead import(
    giveId, fetch_person_decrypted, fetch_photo, getRecordsPeople, identity_public
)
from angelmanSyndromeConnexion.peopleUpdate import updateData
from angelmanSyndromeConnexion.peopleDelete import deleteDataById

from angelmanSyndromeConnexion.pointRemarquable import (
    getRecordsPointsRemarquables, insertPointRemarquable
)

from .common import _get_src, parse_date_any
from app.common.security import ratelimit
from app.common.basic_auth import require_basic

bp = Blueprint("v5_people", __name__)
from .common import register_error_handlers; register_error_handlers(bp)

@bp.route("/people/update", methods=["PATCH", "PUT"])
@ratelimit(3)
@require_basic
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
        raise e
    except Exception as e:
        current_app.logger.exception("Erreur update person")
        return jsonify({"error": f"erreur serveur: {e}"}), 500

@bp.get("/people/<int:person_id>/photo")
@require_basic
def person_photo(person_id: int):
    photo, mime = fetch_photo(person_id)
    if not photo:
        abort(404)
    return Response(photo, mimetype=mime)

@bp.get("/people/<int:person_id>/info")
@require_basic
def person_info(person_id: int):
    result = fetch_person_decrypted(person_id)
    return jsonify(result)

@bp.get("/people/<int:person_id>/infoPublic")
@require_basic
def person_infoPublic(person_id: int):
    result = identity_public(person_id)
    return jsonify(result)

def _payload_people_from_request():
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
            import base64
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
@require_basic
def create_person():
    try:
        fn, ln, email, dob, gt, photo_bytes, long, lat, password, qSec, rSec = _payload_people_from_request()
        new_id = insertData(fn, ln, email, dob, gt, photo_bytes, long, lat, password, qSec, rSec)
        return jsonify({"status": "created", "id": new_id}), 201
    except AppError as e:
        raise e
    except Exception:
        current_app.logger.exception("Unhandled error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@bp.delete("/people/delete/<int:person_id>")
@ratelimit(3)
@require_basic
def api_delete_person_by_id(person_id: int):
    try:
        deleteDataById(person_id)
        return jsonify({"ok": True, "deleted": person_id}), 200
    except AppError as e:
        raise e
    except Exception as e:
        current_app.logger.exception("Erreur suppression par id")
        return jsonify({"error": f"erreur serveur: {e}"}), 500

@bp.get("/people/lookup")
@require_basic
def get_idPerson():
    try:
        email = request.args.get("email") or request.args.get("emailAddress")
        if not email or not email.strip():
            raise MissingFieldError("email (query param) manquant", {"missing": ["email"]})
        person_id = giveId(email)
        return (jsonify({"status": "not_found"}), 404) if person_id is None \
               else (jsonify({"status": "found", "id": person_id}), 200)
    except AppError as e:
        raise e
    except Exception:
        current_app.logger.exception("Unhandled error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

# --------- Points remarquables ----------
def _payload_point_from_request():
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

    return lon, lat, str(short_desc).strip(), str(long_desc).strip()

@bp.post("/pointRemarquable")
@require_basic
def create_pointRemarquable():
    try:
        longitude, latitude, short_desc, long_desc = _payload_point_from_request()
        new_id = insertPointRemarquable(longitude, latitude, short_desc, long_desc)
        from flask import jsonify
        resp = jsonify({"status": "created", "id": new_id})
        resp.status_code = 201
        resp.headers["Location"] = f"/api/v5/pointRemarquable/{new_id}"
        return resp
    except AppError as e:
        raise e
    except Exception:
        current_app.logger.exception("Unhandled error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@bp.get("/peopleMapRepresentation")
@require_basic
def peopleMapRepresentation():
    df = getRecordsPeople()
    return jsonify(df.to_dict(orient="records"))

@bp.get("/pointRemarquableRepresentation")
@require_basic
def pointRemarquableRepresentation():
    df = getRecordsPointsRemarquables()
    return jsonify(df.to_dict(orient="records"))
