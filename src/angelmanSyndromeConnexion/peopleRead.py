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
        text("SELECT photo, photo_mime FROM T_People_Identity WHERE person_id=:person_id"),
        return_result=True,
        params={"person_id": int(person_id)},
    )
    if not rows:
        return None, None
    photo, mime = rows[0]
    return photo, (mime or "image/jpeg")

def identity_public(person_id: int) -> dict | None:
    row = _run_query(text("""
                SELECT
                city, age_years, pseudo, status 
                FROM T_People_Public 
                WHERE id = :id
                """),
            return_result=True, params={"id": int(person_id)}
    )

    if not row:
        return None
    else:
        r = row[0]
        return {
            "id": person_id,
            "city": r[0],
            "age": r[1],
            "pseudo" : r[2],
            "status" : r[3],
        }


def fetch_person_decrypted(person_id: int) -> dict | None:
    row = _run_query(text("""
                SELECT
                p.id,
                p.city, p.age_years, p.pseudo, p.status,
                i.firstname, i.lastname, i.emailAddress, i.dateOfBirth,
                i.genotype, i.longitude, i.latitude, 
                i.secret_question, i.secret_answer
                FROM T_People_Public   AS p
                JOIN T_People_Identity AS i
                ON i.person_id = p.id
                WHERE p.id = :id
                LIMIT 1
                """),
        return_result=True, params={"id": int(person_id)}
    )
    
    if not row:
        return None

    r = row[0]
    city = r[1]
    age = r[2]
    pseudo = r[3]
    status = r[4]
    fn   = crypto.decrypt_bytes_to_str_strict(r[5])
    ln   = crypto.decrypt_bytes_to_str_strict(r[6])
    em   = crypto.decrypt_bytes_to_str_strict(r[7])
    dobS = crypto.decrypt_bytes_to_str_strict(r[8])
    gt   = crypto.decrypt_bytes_to_str_strict(r[9])
    lon  = crypto.decrypt_number(r[10])
    lat  = crypto.decrypt_number(r[11])
    sq   = int(crypto.decrypt_number(r[12])) if r[12] is not None else None
    sa   = crypto.decrypt_bytes_to_str_strict(r[13]) if r[13] is not None else None

    return {
        "id": r[0],
        "firstname": fn,
        "lastname": ln,
        "pseudo" : pseudo,
        "status" : status,
        "email": em,
        "dateOfBirth": date.fromisoformat(dobS) if dobS else None,
        "genotype": gt,
        "city": city,
        "age": age,
        "longitude": lon,
        "latitude": lat,
        "secret_question": sq,
        "secret_answer": sa,
    }


def fetch_person_decrypted_simple(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT person_id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, longitude, latitude 
                FROM T_People_Identity WHERE person_id=:person_id"""),
        return_result=True, params={"person_id": person_id}
    )

    if not row:
        return None
    
    r = row[0]
    fn  = crypto.decrypt_bytes_to_str_strict(r[1])
    ln  = crypto.decrypt_bytes_to_str_strict(r[2])
    em  = crypto.decrypt_bytes_to_str_strict(r[3])
    dob = crypto.decrypt_bytes_to_str_strict(r[4])
    gt  = crypto.decrypt_bytes_to_str_strict(r[5])
    long = crypto.decrypt_number(r[7])
    lat = crypto.decrypt_number(r[8])
      

    return {
        "id": r[0],
        "firstname": fn,
        "lastname": ln,
        "email": em,
        "dateOfBirth": date.fromisoformat(dob) if dob else None,
        "genotype": gt,
        "photo_mime": r[6],
        "longitude" : long,
        "latitude" : lat,
    }

def getRecordsPeople():

    #Only need City, Id, Firstname, LastName, Genotype
    rows = _run_query(
        text("SELECT id, city, age_years FROM T_People_Public ORDER BY id"),
        return_result=True)

    data = []
    for row in rows:
        # Compatibilité selon la version de SQLAlchemy
        try:
            m = row._mapping   # SA 1.4+/2.0
        except AttributeError:
            m = dict(row)      # fallback

        pid = m["id"]
        city = m["city"]
        age = m["age_years"]

        # Ta fonction existante qui renvoie les champs déchiffrés PII
        person = fetch_person_decrypted_simple(pid)
        if not person:
            continue

        data.append({
            "id": pid,
            "firstname": person.get("firstname"),
            "lastname": person.get("lastname"),
            "city": city,                 # on prend la ville de la table publique
            "age": age,                   # remap age_years -> age pour la sortie
            "genotype": person.get("genotype"),
            "longitude": person.get("longitude"),
            "latitude": person.get("latitude"),
        })

    df = pd.DataFrame(data, columns=["id","firstname","lastname","city","age","genotype","longitude","latitude"])
    return df


def giveId(email_real):
    sha = crypto.email_sha256(email_real)
    row = _run_query(
        text("SELECT person_id FROM T_People_Identity WHERE email_sha = :sha LIMIT 1"),
        return_result=True,
        params={"sha": sha},
    )
    return int(row[0][0]) if row else None

def getQuestionSecrete(person_id: int) -> int | None:
    rows = _run_query(
        text("""SELECT secret_question FROM T_People_Identity WHERE person_id = :person_id LIMIT 1"""),
        params={"person_id": int(person_id)},
        return_result=True,
    )
    if not rows:
        return None
    sq_enc = rows[0][0]
    try:
        return int(crypto.decrypt_number(sq_enc)) if sq_enc is not None else None
    except Exception:
        return None
