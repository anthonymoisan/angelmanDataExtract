from __future__ import annotations

from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

#update des metaData pour un membre donné
def setMemberMetaData(session,member,last_read_message_id):
    member.last_read_message_id = last_read_message_id
    member.last_read_at = utc_now()
    session.commit()