# src/app/v1/routes.py
from flask import Blueprint
from app.common.db_read import _read_table_as_json   # ⬅️ absolu

bp = Blueprint("v1", __name__)

@bp.get("/resources/ASTrials")
def api_as_trials_all():
    return _read_table_as_json("T_ASTrials")

@bp.get("/resources/articlesPubMed")
def api_articles_all():
    return _read_table_as_json("T_ArticlesPubMed")

@bp.get("/resources/UnPopulation")
def api_unpopulation_all():
    return _read_table_as_json("T_UnPopulation")

@bp.get("/resources/ClinicalTrials")
def api_clinicaltrials_all():
    return _read_table_as_json("T_ClinicalTrials")
