import sys, os
from sqlalchemy import text
import pandas as pd
from pathlib import Path
import json
from angelmanSyndromeConnexion.utils_image import (
    detect_mime_from_bytes, normalize_mime, recompress_image
)
from angelmanSyndromeConnexion import error

# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from tools.utilsTools import _insert_data, _run_query
from tools.logger import setup_logger

# Set up logger
logger = setup_logger(debug=False)

def insertPointRemarquable(longitude, latitude, short_desc, long_desc, photo):
    logger.info(
        "Insert point | lon=%.6f lat=%.6f | short=%r",
        longitude, latitude, short_desc
    )

    # -------- 1bis) Photo : recompression et choix final --------
    photo_blob_final = None
    photo_mime_final = None

    if photo is not None:
        # Détection MIME robuste (indépendant de l'extension)
        detected_mime = detect_mime_from_bytes(photo)  # p.ex. "image/jpeg"
        src_mime = normalize_mime(detected_mime or "image/jpeg")
        if src_mime not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
            raise error.InvalidMimeTypeError(f"MIME non autorisé: {src_mime}")

        # Tenter une recompression (doit renvoyer (blob, mime) ou (None, None))
        try:
            new_blob, new_mime = recompress_image(photo)
        except Exception as e:
            logger.warning("Recompression échouée: %s", e, exc_info=True)
            new_blob, new_mime = None, None

        # Choisir la meilleure version (garder original si pas plus petit)
        if new_blob and len(new_blob) < len(photo):
            photo_blob_final = new_blob
            photo_mime_final = normalize_mime(new_mime or src_mime)
        else:
            photo_blob_final = photo
            photo_mime_final = src_mime

        # Contrôle de taille APRÈS recompression/fallback (contrainte DB)
        if len(photo_blob_final) > 4 * 1024 * 1024:
            raise error.PhotoTooLargeError("Photo > 4 MiB après recompression")
    else:
        photo_blob_final = None
        photo_mime_final = None  # cohérence avec vos CHECK


    lon = float(longitude); lat = float(latitude)
    if not (-180 <= lon <= 180): raise ValueError("longitude hors plage [-180,180]")
    if not (-90 <= lat <= 90):   raise ValueError("latitude hors plage [-90,90]")
    if not short_desc or not str(short_desc).strip():
        raise ValueError("short_desc est obligatoire")

    wkt = f"POINT({lon} {lat})"

    sql = text("""
        INSERT INTO T_PointRemarquable (longitude, latitude, short_desc, long_desc,photo, photo_mime, geom)
        VALUES (:lon, :lat, :sd, :ld, :photo, :photo_mime, ST_GeomFromText(:wkt, 4326))
        -- Variante si supportée par ta version:
        -- VALUES (:lon, :lat, :sd, :ld, ST_SRID(POINT(:lon, :lat), 4326))
    """)
    try:
        _run_query(
        sql,
        params={"lon": lon, "lat": lat, "sd": short_desc, "ld": long_desc, "photo":photo_blob_final , "photo_mime":photo_mime_final, "wkt": wkt},
        bAngelmanResult=False
    )
    except Exception:
        logger.error("Erreur dans insert T_PointRemarquable")
        raise

    try:
        #Fonctionne avec Count(*) car on ne supprime pas d'éléments dans T_PointRemarquable
        lastRowId = _run_query(
        text("SELECT COUNT(*) FROM T_PointRemarquable"),
        return_result=True,
        bAngelmanResult=False)
        return lastRowId[0][0]
    except Exception:
        logger.error("Insert failed in T_PointRemarquable")
        raise

def record(record_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, longitude, latitude, short_desc, long_desc,
                       geom
                FROM T_PointRemarquable WHERE id=:id"""),
        return_result=True, paramsSQL={"id": record_id},bAngelmanResult=False
    )

    if not row:
        return None
    
    return {
        "id": row[0][0],
        "longitude": row[0][1],
        "latitude": row[0][2],
        "short_desc": row[0][3],
        "long_desc": row[0][4],
        "geom": row[0][5],
        
    }

def getRecordsPointsRemarquables():
    rows = _run_query(text("""
        SELECT
          id,
          longitude,
          latitude,
          short_desc,
          long_desc,
          (photo IS NOT NULL) AS has_photo,
          photo_mime,
          ST_AsText(geom)    AS wkt,      -- "POINT(lon lat)"
          ST_AsGeoJSON(geom) AS geojson   -- '{"type":"Point",...}'
        FROM T_PointRemarquable
        ORDER BY id
    """), return_result=True, bAngelmanResult=False)

    data = []
    for r in rows:
        data.append({
            "id":         int(r[0]),
            "longitude":  float(r[1]),
            "latitude":   float(r[2]),
            "short_desc": r[3],
            "long_desc":  r[4],
            "has_photo":  r[5],
            "photo_mime": r[6],
            "wkt":        r[7],                # str, JSON-friendly
            "geojson":    json.loads(r[8]),    # dict, JSON-friendly
        })
    return pd.DataFrame(data, columns=["id","longitude","latitude","short_desc","long_desc", "has_photo", "photo_mime","wkt","geojson"])

def fetch_photo(id: int) -> tuple[bytes | None, str | None]:
    rows = _run_query(
        text("SELECT photo, photo_mime FROM T_PointRemarquable WHERE id=:id"),
        return_result=True,
        params={"id": int(id)},
        bAngelmanResult=False
    )
    if not rows:
        return None, None
    photo, mime = rows[0]
    return photo, (mime or "image/jpeg")
