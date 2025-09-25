import sys, os
from sqlalchemy import text
import pandas as pd
from utilsTools import _insert_data
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger
from utilsTools import _run_query

# Set up logger
logger = setup_logger(debug=False)

def insertPointRemarquable(longitude, latitude, short_desc, long_desc):
    logger.info(
        "Insert point | lon=%.6f lat=%.6f | short=%r",
        longitude, latitude, short_desc
    )

    lon = float(longitude); lat = float(latitude)
    if not (-180 <= lon <= 180): raise ValueError("longitude hors plage [-180,180]")
    if not (-90 <= lat <= 90):   raise ValueError("latitude hors plage [-90,90]")
    if not short_desc or not str(short_desc).strip():
        raise ValueError("short_desc est obligatoire")

    wkt = f"POINT({lon} {lat})"

    sql = text("""
        INSERT INTO T_PointRemarquable (longitude, latitude, short_desc, long_desc, geom)
        VALUES (:lon, :lat, :sd, :ld, ST_GeomFromText(:wkt, 4326))
        -- Variante si supportée par ta version:
        -- VALUES (:lon, :lat, :sd, :ld, ST_SRID(POINT(:lon, :lat), 4326))
    """)
    try:
        _run_query(sql, paramsSQL={"lon": lon, "lat": lat, "sd": short_desc, "ld": long_desc, "wkt": wkt})
    except Exception:
        logger.error("Erreur dans insert T_PointRemarquable")
        raise

    try:
        lastRowId = _run_query(
        text("SELECT COUNT(*) FROM T_PointRemarquable"),
        return_result=True)
        return lastRowId[0][0]
    except Exception:
        logger.error("Insert failed in T_PointRemarquable")
        raise

def record(record_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, longitude, latitude, short_desc, long_desc,
                       geom
                FROM T_PointRemarquable WHERE id=:id"""),
        return_result=True, paramsSQL={"id": record_id}
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

from sqlalchemy import text
import pandas as pd
import json

def getRecordsPointsRemarquables():
    rows = _run_query(text("""
        SELECT
          id,
          longitude,
          latitude,
          short_desc,
          long_desc,
          ST_AsText(geom)    AS wkt,      -- "POINT(lon lat)"
          ST_AsGeoJSON(geom) AS geojson   -- '{"type":"Point",...}'
        FROM T_PointRemarquable
        ORDER BY id
    """), return_result=True)

    data = []
    for r in rows:
        data.append({
            "id":         int(r[0]),
            "longitude":  float(r[1]),
            "latitude":   float(r[2]),
            "short_desc": r[3],
            "long_desc":  r[4],
            "wkt":        r[5],                # str, JSON-friendly
            "geojson":    json.loads(r[6]),    # dict, JSON-friendly
        })
    return pd.DataFrame(data, columns=["id","longitude","latitude","short_desc","long_desc","wkt","geojson"])
