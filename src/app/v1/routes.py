# src/app/v1/routes.py
from flask import Blueprint
from app.common.db_read import _read_table_as_json   # ⬅️ absolu
from app.common.basic_auth import require_basic
from app.common.security import ratelimit

bp = Blueprint("v1", __name__)

@bp.get("/resources/ASTrials")
@require_basic
@ratelimit(5)
def api_as_trials_all():
    return _read_table_as_json("T_ASTrials",decrypt=False)

@bp.get("/resources/articlesPubMed")
@require_basic
@ratelimit(5)
def api_articles_all():
    return _read_table_as_json("T_ArticlesPubMed",decrypt=False)

@bp.get("/resources/UnPopulation")
@require_basic
@ratelimit(5)
def api_unpopulation_all():
    return _read_table_as_json("T_UnPopulation",decrypt=False)

@bp.get("/resources/ClinicalTrials")
@require_basic
@ratelimit(5)
def api_clinicaltrials_all():
    return _read_table_as_json("T_ClinicalTrials",decrypt=False)
