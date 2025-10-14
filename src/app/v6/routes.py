# app/v6/routes.py
from __future__ import annotations
import json
import os
from flask import jsonify, Blueprint
from app.common.basic_auth import require_basic

bp = Blueprint("v6", __name__)

def _data_dir() -> str:
    """
    Retourne le chemin absolu du dossier 'data' au même niveau que 'src/'.
    Hypothèse arbo : src/
                      ├── app/
                     data/
    """
    app_dir = os.path.dirname(os.path.dirname(__file__))   # .../src/app
    data_dir = os.path.abspath(os.path.join(app_dir, "../..", "data"))
    return data_dir

def _load_json(filename: str):
    """
    Charge un fichier JSON depuis le dossier data et renvoie jsonify(payload).
    """
    path = os.path.join(_data_dir(), filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@bp.get("/resources/PharmaceuticalOffice")
@require_basic
def api_pharmaceutical_office():
    return _load_json("pharmaceuticalOffice.json")

@bp.get("/resources/Ime")
@require_basic
def api_ime():
    return _load_json("ime.json")

@bp.get("/resources/Mas")
@require_basic
def api_mas():
    return _load_json("mas.json")

@bp.get("/resources/Fam")
@require_basic
def api_fam():
    return _load_json("fam.json")

@bp.get("/resources/Mdph")
@require_basic
def api_mdph():
    return _load_json("mdph.json")

@bp.get("/resources/Camps")
@require_basic
def api_camps():
    return _load_json("camps.json")
