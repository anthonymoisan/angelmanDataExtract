# src/angelmanSyndromeConnexion/peopleRead.py
from __future__ import annotations
from datetime import date
import pandas as pd
from sqlalchemy import text

from tools.logger import setup_logger
from tools.utilsTools import _run_query
import tools.crypto_utils as crypto

logger = setup_logger(debug=False)


def fetch_photo(person_id: int) -> tuple[bytes | None, str | None]:
    rows = _run_query(
        text("SELECT photo, photo_mime FROM T_ASPeople WHERE id=:id"),
        return_result=True,
        params={"id": int(person_id)},
    )
    if not rows:
        return None, None
    photo, mime = rows[0]
    return photo, (mime or "image/jpeg")


def fetch_person_decrypted(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, city, longitude, latitude, age, 
                       secret_question, secret_answer 
                FROM T_ASPeople WHERE id=:id"""),
        return_result=True, params={"id": int(person_id)}
    )
    if not row:
        return None

    r = row[0]
    fn   = crypto.decrypt_bytes_to_str_strict(r[1])
    ln   = crypto.decrypt_bytes_to_str_strict(r[2])
    em   = crypto.decrypt_bytes_to_str_strict(r[3])
    dobS = crypto.decrypt_bytes_to_str_strict(r[4])
    gt   = crypto.decrypt_bytes_to_str_strict(r[5])
    ci   = crypto.decrypt_bytes_to_str_strict(r[7])
    lon  = crypto.decrypt_number(r[8])
    lat  = crypto.decrypt_number(r[9])
    age  = crypto.decrypt_number(r[10])
    sq   = int(crypto.decrypt_number(r[11])) if r[11] is not None else None
    sa   = crypto.decrypt_bytes_to_str_strict(r[12]) if r[12] is not None else None

    return {
        "id": r[0],
        "firstname": fn,
        "lastname": ln,
        "email": em,
        "dateOfBirth": date.fromisoformat(dobS) if dobS else None,
        "genotype": gt,
        "photo_mime": r[6],
        "city": ci,
        "age": age,
        "longitude": lon,
        "latitude": lat,
        "secret_question": sq,
        "secret_answer": sa,
    }


def fetch_person_decrypted_simple(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, city, longitude, latitude, age 
                FROM T_ASPeople WHERE id=:id"""),
        return_result=True, params={"id": int(person_id)}
    )
    if not row:
        return None

    r = row[0]
    fn   = crypto.decrypt_bytes_to_str_strict(r[1])
    ln   = crypto.decrypt_bytes_to_str_strict(r[2])
    em   = crypto.decrypt_bytes_to_str_strict(r[3])
    dobS = crypto.decrypt_bytes_to_str_strict(r[4])
    gt   = crypto.decrypt_bytes_to_str_strict(r[5])
    ci   = crypto.decrypt_bytes_to_str_strict(r[7])
    lon  = crypto.decrypt_number(r[8])
    lat  = crypto.decrypt_number(r[9])
    age  = crypto.decrypt_number(r[10])

    return {
        "id": r[0],
        "firstname": fn,
        "lastname": ln,
        "email": em,
        "dateOfBirth": date.fromisoformat(dobS) if dobS else None,
        "genotype": gt,
        "photo_mime": r[6],
        "city": ci,
        "age": age,
        "longitude": lon,
        "latitude": lat,
    }


def getRecordsPeople() -> pd.DataFrame:
    ids = _run_query(
        text("SELECT id FROM T_ASPeople ORDER BY id"),
        return_result=True
    )
    data = []
    for (pid,) in ids:
        person = fetch_person_decrypted_simple(pid)
        if not person:
            continue
        data.append({
            "id": pid,
            "firstname": person["firstname"],
            "lastname": person["lastname"],
            "city": person["city"],
            "age": person["age"],
            "genotype": person["genotype"],
            "longitude": person["longitude"],
            "latitude": person["latitude"],
        })
    return pd.DataFrame(
        data,
        columns=["id", "firstname", "lastname", "city", "age", "genotype", "longitude", "latitude"]
    )


def giveId(email_real: str) -> int | None:
    sha = crypto.email_sha256(email_real)
    row = _run_query(
        text("SELECT id FROM T_ASPeople WHERE email_sha = :sha LIMIT 1"),
        return_result=True,
        params={"sha": sha},
    )
    return int(row[0][0]) if row else None


def getQuestionSecrete(person_id: int) -> int | None:
    rows = _run_query(
        text("""SELECT secret_question FROM T_ASPeople WHERE id = :id LIMIT 1"""),
        params={"id": int(person_id)},
        return_result=True,
    )
    if not rows:
        return None
    sq_enc = rows[0][0]
    try:
        return int(crypto.decrypt_number(sq_enc)) if sq_enc is not None else None
    except Exception:
        return None
