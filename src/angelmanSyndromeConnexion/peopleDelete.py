# src/angelmanSyndromeConnexion/peopleDelete.py
from __future__ import annotations
from sqlalchemy import text

from tools.logger import setup_logger
from tools.utilsTools import _run_query

logger = setup_logger(debug=False)

from sqlalchemy import text

def deleteDataById(person_id: int) -> int:
    """
    Supprime une personne + ses messages envoyés + conversations 1-1 (is_group=0) orphelines.
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

    _run_query(text("START TRANSACTION"), bAngelmanResult=False)
    try:
        # 1) Conserver la liste des conversations 1-1 où la personne est membre (avant suppression)
        conv_rows = _run_query(
            text("""
                SELECT cm.conversation_id
                FROM T_Conversation_Member cm
                JOIN T_Conversation c ON c.id = cm.conversation_id
                WHERE cm.people_public_id = :id
                  AND c.is_group = 0
            """),
            params={"id": pid},
            return_result=True,
            bAngelmanResult=False
        )
        conv_ids = [r[0] if not isinstance(r, dict) else r["conversation_id"] for r in (conv_rows or [])]

        # 2) Supprimer les messages envoyés (sinon FK RESTRICT bloque)
        _run_query(
            text("DELETE FROM T_Message WHERE sender_people_id = :id"),
            params={"id": pid},
            bAngelmanResult=False
        )

        # 3) Supprimer le membership de la personne
        _run_query(
            text("DELETE FROM T_Conversation_Member WHERE people_public_id = :id"),
            params={"id": pid},
            bAngelmanResult=False
        )

        # 4) Supprimer les conversations 1-1 devenues invalides (≠ 2 membres)
        #    On limite uniquement aux conv 1-1 où elle était membre.
        if conv_ids:
            placeholders = ", ".join([f":c{i}" for i in range(len(conv_ids))])
            params = {f"c{i}": conv_ids[i] for i in range(len(conv_ids))}

            orphan_rows = _run_query(
                text(f"""
                    SELECT cm.conversation_id
                    FROM T_Conversation_Member cm
                    JOIN T_Conversation c ON c.id = cm.conversation_id
                    WHERE c.is_group = 0
                      AND cm.conversation_id IN ({placeholders})
                    GROUP BY cm.conversation_id
                    HAVING COUNT(*) <> 2
                """),
                params=params,
                return_result=True,
                bAngelmanResult=False
            )
            orphan_ids = [r[0] if not isinstance(r, dict) else r["conversation_id"] for r in (orphan_rows or [])]

            if orphan_ids:
                placeholders2 = ", ".join([f":d{i}" for i in range(len(orphan_ids))])
                params2 = {f"d{i}": orphan_ids[i] for i in range(len(orphan_ids))}

                # Supprimer la conversation -> cascade vers messages + members (et attachments/reactions via messages)
                _run_query(
                    text(f"DELETE FROM T_Conversation WHERE id IN ({placeholders2})"),
                    params=params2,
                    bAngelmanResult=False
                )

        # 5) Supprimer l'identité (optionnel, car People_Public -> Identity est ON DELETE CASCADE)
        _run_query(
            text("DELETE FROM T_People_Identity WHERE person_id = :id"),
            params={"id": pid},
            bAngelmanResult=False
        )

        # 6) Supprimer la personne
        _run_query(
            text("DELETE FROM T_People_Public WHERE id = :id"),
            params={"id": pid},
            bAngelmanResult=False
        )

        _run_query(text("COMMIT"), bAngelmanResult=False)
        return 1

    except Exception:
        _run_query(text("ROLLBACK"), bAngelmanResult=False)
        raise
