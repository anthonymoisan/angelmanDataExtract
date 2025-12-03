# app/v5/public/proxy_pointRemarquable.py
from __future__ import annotations

import base64
from flask import Blueprint, jsonify, request, Response, abort, current_app

from angelmanSyndromeConnexion.error import (
    AppError,
    MissingFieldError,
    ValidationError,
)
from angelmanSyndromeConnexion.pointRemarquable import (
    getRecordsPointsRemarquables,
    insertPointRemarquable,
    fetch_point_photo,
)

from ..common import _get_src, register_error_handlers
from app.common.security import require_public_app_key

bp = Blueprint("public_pointRemarquable", __name__)
register_error_handlers(bp)

# --------------------------------------------------------------------
# Utilitaires locaux (reprise des helpers de app/v5/people.py)
# --------------------------------------------------------------------
def _payload_point_from_request():
    """
    Même logique que dans app/v5/people.py pour les points remarquables.
    """
    src = _get_src()
    raw_lon = src.get("longitude") or src.get("lon")
    raw_lat = src.get("latitude") or src.get("lat")
    short_desc = src.get("short_desc") or src.get("short") or src.get("title")
    long_desc = src.get("long_desc") or src.get("description") or ""
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


# --------------------------------------------------------------------
# Routes PUBLIC -> logique interne (sans HTTP requests)
# --------------------------------------------------------------------

# Point Remarquable - création (JSON)
@bp.post("/pointRemarquable")
@require_public_app_key
def public_create_point_remarquable():
    try:
        longitude, latitude, short_desc, long_desc, photo_bytes = _payload_point_from_request()
        new_id = insertPointRemarquable(longitude, latitude, short_desc, long_desc,photo_bytes)
        resp = jsonify({"status": "created", "id": new_id})
        resp.status_code = 201
        resp.headers["Location"] = f"/api/public/pointRemarquable/{new_id}"
        return resp
    except AppError as e:
        raise e
    except Exception:
        current_app.logger.exception(
            "Unhandled error (public_create_point_remarquable)"
        )
        return (
            jsonify({"status": "error", "message": "Internal server error"}),
            500,
        )


# Point Remarquable - liste (JSON)
@bp.get("/pointRemarquableRepresentation")
@require_public_app_key
def public_point_remarquable_representation():
    try:
        df = getRecordsPointsRemarquables()
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        current_app.logger.exception(
            "[PUBLIC_PROXY][POINT] pointRemarquableRepresentation ERROR: %s", e
        )
        return (
            jsonify(
                {"error": f"pointRemarquableRepresentation error: {e}"}
            ),
            500,
        )

@bp.get("/pointRemarquable/<int:point_id>/photo")
@require_public_app_key
def public_point_remarquable_photo(point_id: int):
    photo, mime = fetch_point_photo(point_id)  
    if not photo:
        abort(404)
    return Response(photo, mimetype=mime)