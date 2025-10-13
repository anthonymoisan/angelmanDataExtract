from flask import Blueprint
from app.common.db_read import _read_table_as_json

bp = Blueprint("v3", __name__)

@bp.get("/resources/Map_Global")
def map_global():
    return _read_table_as_json("T_MapGlobal")