from flask import Blueprint
from app.common.db_read import _read_table_as_json
from app.common.basic_auth import require_basic
from app.common.security import ratelimit

bp = Blueprint("v3", __name__)

@bp.get("/resources/Map_Global")
@require_basic
@ratelimit(5)
def map_global():
    return _read_table_as_json("T_MapGlobal")


@bp.get("/resources/Map_ASConnect")
@require_basic
@ratelimit(5)
def map_ASConnect():
    return _read_table_as_json("T_MapASConnect")
