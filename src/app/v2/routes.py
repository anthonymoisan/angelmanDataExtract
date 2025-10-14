from flask import Blueprint
from app.common.db_read import _read_table_as_json
from app.common.basic_auth import require_basic
from app.common.security import ratelimit

bp = Blueprint("v2", __name__)

# ---------- FAST_France ----------
@bp.get("/resources/FAST_France/MapFrance_French")
@require_basic
@ratelimit(5)
def map_france_french():
    return _read_table_as_json("T_MapFrance_French")

@bp.get("/resources/FAST_France/DifficultiesSA_French")
@require_basic
@ratelimit(5)
def difficulties_sa_french():
    return _read_table_as_json("T_MapFrance_DifficultiesSA_French")

@bp.get("/resources/FAST_France/RegionDepartement_French")
@require_basic
@ratelimit(5)
def region_departement_french():
    return _read_table_as_json("T_MapFrance_RegionDepartement_French")

@bp.get("/resources/FAST_France/RegionPrefecture_French")
@require_basic
@ratelimit(5)
def region_prefecture_french():
    return _read_table_as_json("T_MapFrance_RegionPrefecture_French")

@bp.get("/resources/FAST_France/MapFrance_English")
@require_basic
@ratelimit(5)
def map_france_english():
    return _read_table_as_json("T_MapFrance_English")

@bp.get("/resources/FAST_France/DifficultiesSA_English")
@require_basic
@ratelimit(5)
def difficulties_sa_english():
    return _read_table_as_json("T_MapFrance_DifficultiesSA_English")

@bp.get("/resources/FAST_France/Capabilities_English")
@require_basic
@ratelimit(5)
def capabilities_english():
    return _read_table_as_json("T_MapFrance_Capabilitie")

@bp.get('/resources/FAST_Latam/MapLatam_Spanish')
@require_basic
@ratelimit(5)
def map_Latam_spanish():
    return _read_table_as_json('T_MapLatam_Spanish')

@bp.get('/resources/FAST_Latam/MapLatam_English')
@require_basic
@ratelimit(5)
def map_Latam_english():
    return _read_table_as_json('T_MapLatam_English')

@bp.get('/resources/FAST_Latam/Capabilities_English')
@require_basic
@ratelimit(5)
def capabilities_Latam_english():
    """
    API to expose the results from Capabilities in English with the specific table from the database
    """
    return _read_table_as_json('T_MapLatam_Capabilitie')

