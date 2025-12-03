# app/v5/pointRemarquable.py
from __future__ import annotations
import base64
from flask import Blueprint, jsonify, request, Response, abort, current_app

from angelmanSyndromeConnexion.error import (
    AppError, MissingFieldError, ValidationError
)

from angelmanSyndromeConnexion.pointRemarquable import (
    getRecordsPointsRemarquables, insertPointRemarquable, fetch_point_photo
)

from .common import _get_src
from app.common.basic_auth import require_basic,require_internal

bp = Blueprint("v5_pointRemarquable", __name__)
bp.before_request(require_internal)

from .common import register_error_handlers; register_error_handlers(bp)

# --------- Points remarquables ----------
def _payload_point_from_request():
    src = _get_src()
    raw_lon = src.get("longitude") or src.get("lon")
    raw_lat = src.get("latitude")  or src.get("lat")
    short_desc = src.get("short_desc") or src.get("short") or src.get("title")
    long_desc  = src.get("long_desc")  or src.get("description") or ""

    if request.content_type and request.content_type.startswith("multipart/form-data"):
        file = request.files.get("photo")
        photo_bytes = file.read() if file else None
    else:
        data = request.get_json(silent=True) or {}
        photo_b64 = data.get("photo_base64")
        if photo_b64:
            if "," in photo_b64:
                photo_b64 = photo_b64.split(",", 1)[1]
            photo_bytes = base64.b64decode(photo_b64)
        else:
            photo_bytes = None

    missing = []

    def _miss(v):
        return v is None or (isinstance(v, str) and v.strip() == "")

    if _miss(raw_lon):
        missing.append("longitude")
    if _miss(raw_lat):
        missing.append("latitude")
    if _miss(short_desc):
        missing.append("short_desc")

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

    return lon, lat, str(short_desc).strip(), str(long_desc).strip(), photo_bytes

@bp.post("/pointRemarquable")
@require_basic
def create_pointRemarquable():
    try:
        longitude, latitude, short_desc, long_desc, photo_bytes = _payload_point_from_request()
        new_id = insertPointRemarquable(longitude, latitude, short_desc, long_desc, photo_bytes)
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

@bp.get("/pointRemarquableRepresentation")
@require_basic
def pointRemarquableRepresentation():
    df = getRecordsPointsRemarquables()
    return jsonify(df.to_dict(orient="records"))

@bp.get("/pointRemarquable/<int:point_id>/photo")
@require_basic
def pointRemarquablePhoto(point_id: int):
    photo, mime = fetch_point_photo(point_id)  
    if not photo:
        abort(404)
    return Response(photo, mimetype=mime)