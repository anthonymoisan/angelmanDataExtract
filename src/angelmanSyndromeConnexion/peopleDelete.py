# src/angelmanSyndromeConnexion/peopleDelete.py
from __future__ import annotations
from sqlalchemy import text

from tools.logger import setup_logger
from tools.utilsTools import _run_query

logger = setup_logger(debug=False)


def deleteDataById(person_id: int) -> int:
    """
    Supprime une personne par ID.
    Retourne 1 si supprimé, 0 si inexistant.
    """
    pid = int(person_id)

    exists_rows = _run_query(
        text("SELECT 1 FROM T_People_Public WHERE id = :id LIMIT 1"),
        params={"id": pid},
        return_result=True,
        bAngelmanResult=False
    )
    if not exists_rows:
        return 0

    _run_query(text("DELETE FROM T_People_Public WHERE id = :id"), params={"id": pid},bAngelmanResult=False)
    return 1
