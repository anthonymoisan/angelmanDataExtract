# src/app/v1/routes.py
from flask import Blueprint
from app.common.db_read import _read_table_as_json   # ⬅️ absolu
from app.common.basic_auth import require_basic

bp = Blueprint("v1", __name__)

@bp.get("/resources/ASTrials")
@require_basic
def api_as_trials_all():
    return _read_table_as_json("T_ASTrials")

@bp.get("/resources/articlesPubMed")
@require_basic
def api_articles_all():
    return _read_table_as_json("T_ArticlesPubMed")

@bp.get("/resources/UnPopulation")
@require_basic
def api_unpopulation_all():
    return _read_table_as_json("T_UnPopulation")

@bp.get("/resources/ClinicalTrials")
@require_basic
def api_clinicaltrials_all():
    return _read_table_as_json("T_ClinicalTrials")
