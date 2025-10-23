from flask import Blueprint
from app.common.db_read import _read_table_as_json
from app.common.basic_auth import require_basic
from app.common.security import ratelimit


bp = Blueprint("v4", __name__)

# -------- Poland --------
@bp.get("/resources/FAST_Poland/MapPoland_Polish")
@require_basic
@ratelimit(5)
def map_poland_pl():
    return _read_table_as_json("T_MapPoland_Polish")

@bp.get("/resources/FAST_Poland/MapPoland_English")
@require_basic
@ratelimit(5)
def map_poland_en():
    return _read_table_as_json("T_MapPoland_English")


# -------- Spain --------
@bp.get("/resources/FAST_Spain/MapSpain_Spanish")
@require_basic
@ratelimit(5)
def map_spain_es():
    return _read_table_as_json("T_MapSpain_Spanish")

@bp.get("/resources/FAST_Spain/MapSpain_English")
@require_basic
@ratelimit(5)
def map_spain_en():
    return _read_table_as_json("T_MapSpain_English")


# -------- Italy --------
@bp.get("/resources/Italy/MapItaly_English")
@require_basic
@ratelimit(5)
def map_italy_en():
    return _read_table_as_json("T_MapItaly_English")

@bp.get("/resources/Italy/MapItaly_Italian")
@require_basic
@ratelimit(5)
def map_italy_it():
    return _read_table_as_json("T_MapItaly_Italian")


# -------- Germany --------
@bp.get("/resources/Germany/MapGermany_English")
@require_basic
@ratelimit(5)
def map_germany_en():
    return _read_table_as_json("T_MapGermany_English")

@bp.get("/resources/Germany/MapGermany_Deutsch")
@require_basic
@ratelimit(5)
def map_germany_de():
    return _read_table_as_json("T_MapGermany_Deutsch")


# -------- Brazil --------
@bp.get("/resources/Brazil/MapBrazil_English")
@require_basic
@ratelimit(5)
def map_brazil_en():
    return _read_table_as_json("T_MapBrazil_English")

@bp.get("/resources/Brazil/MapBrazil_Portuguese")
@require_basic
@ratelimit(5)
def map_brazil_pt():
    return _read_table_as_json("T_MapBrazil_Portuguese")


# -------- Australia --------
@bp.get("/resources/Australia/MapAustralia_English")
@require_basic
@ratelimit(5)
def map_australia_en():
    return _read_table_as_json("T_MapAustralia_English")


# -------- USA --------
@bp.get("/resources/USA/MapUSA_English")
@require_basic
@ratelimit(5)
def map_usa_en():
    return _read_table_as_json("T_MapUSA_English")


# -------- Canada --------
@bp.get("/resources/Canada/MapCanada_English")
@require_basic
@ratelimit(5)
def map_canada_en():
    return _read_table_as_json("T_MapCanada_English")


# -------- UK --------
@bp.get("/resources/UK/MapUK_English")
@require_basic
@ratelimit(5)
def map_uk_en():
    return _read_table_as_json("T_MapUK_English")


# -------- India --------
@bp.get("/resources/India/MapIndia_English")
@require_basic
@ratelimit(5)
def map_india_en():
    return _read_table_as_json("T_MapIndia_English")

@bp.get("/resources/India/MapIndia_Hindi")
@require_basic
@ratelimit(5)
def map_india_hi():
    return _read_table_as_json("T_MapIndia_Hindi")


# -------- Indonesia --------
@bp.get("/resources/Indonesia/MapIndonesia_English")
@require_basic
@ratelimit(5)
def map_indonesia_en():
    return _read_table_as_json("T_MapIndonesia_English")

@bp.get("/resources/Indonesia/MapIndonesia_Ind")
@require_basic
@ratelimit(5)
def map_indonesia_id():
    return _read_table_as_json("T_MapIndonesia_Ind")


# -------- Greece --------
@bp.get("/resources/Greece/MapGreece_English")
@ratelimit(5)
def map_greece_en():
    return _read_table_as_json("T_MapGreece_English")

@bp.get("/resources/Greece/MapGreece_Greek")
@ratelimit(5)
def map_greece_el():
    return _read_table_as_json("T_MapGreece_Greek")


# -------- Malaysia --------
@bp.get("/resources/Malaysia/MapMalaysia_English")
@ratelimit(5)
def map_malaysia_en():
    return _read_table_as_json("T_MapMalaysia_English")

@bp.get("/resources/Malaysia/MapMalaysia_Malaysian")
@ratelimit(5)
def map_malaysia_ma():
    return _read_table_as_json("T_MapMalaysia_Malaysian")
