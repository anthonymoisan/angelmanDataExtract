# src/angelmanSyndromeConnexion/peopleRead.py
from __future__ import annotations
from datetime import date
import pandas as pd
from sqlalchemy import text
from angelmanSyndromeConnexion.utils_image import recompress_image, normalize_mime
from tools.logger import setup_logger
from tools.utilsTools import _run_query
import tools.crypto_utils as crypto
import time
from angelmanSyndromeConnexion.geo_utils3 import countries_from_iso2_list_sorted_dict
from angelmanSyndromeConnexion.models.people_public import PeoplePublic
from sqlalchemy import select
logger = setup_logger(debug=False)


def fetch_photo(person_id: int) -> tuple[bytes | None, str | None]:
    rows = _run_query(
        text(
            "SELECT photo, photo_mime "
            "FROM T_People_Identity "
            "WHERE person_id=:person_id"
        ),
        return_result=True,
        params={"person_id": int(person_id)},
        bAngelmanResult=False,
    )

    if not rows:
        return None, None

    photo, mime = rows[0]
    if not photo:
        return None, None

    mime = normalize_mime(mime) or "image/jpeg"

    # 🔁 Recompression automatique si HEIC / HEIF
    if mime in ("image/heic", "image/heif"):
        try:
            new_blob, new_mime = recompress_image(
                photo,
                target_format="JPEG",   # ou "WEBP" si tu préfères
                quality=85,
            )
            if new_blob:
                return new_blob, new_mime
        except Exception:
            # fallback silencieux (ne pas casser l'API)
            pass

    return photo, mime

def identity_public(person_id: int) -> dict | None:
    row = _run_query(text("""
                SELECT
                city, country, country_code, age_years, pseudo, status, gender, is_info
                FROM T_People_Public 
                WHERE id = :id
                """),
            return_result=True, params={"id": int(person_id)},bAngelmanResult=False
    )

    if not row:
        return None
    else:
        r = row[0]
        return {
            "id": person_id,
            "city": r[0],
            "age": r[3],
            "pseudo" : r[4],
            "status" : r[5],
            "gender" : r[6],
            "is_info" : r[7],
        }


def fetch_person_decrypted(person_id: int) -> dict | None:
    row = _run_query(text("""
                SELECT
                p.id,
                p.city, p.gender, p.age_years, p.pseudo, p.status, p.is_info,
                i.firstname, i.lastname, i.emailAddress, i.dateOfBirth,
                i.genotype, i.longitude, i.latitude, 
                i.secret_question, i.secret_answer
                FROM T_People_Public   AS p
                JOIN T_People_Identity AS i
                ON i.person_id = p.id
                WHERE p.id = :id
                LIMIT 1
                """),
        return_result=True, params={"id": int(person_id)}, bAngelmanResult=False
    )
    
    if not row:
        return None

    r = row[0]
    city = r[1]
    gender = r[2]
    age = r[3]
    pseudo = r[4]
    status = r[5]
    is_info = r[6]
    fn   = crypto.decrypt_bytes_to_str_strict(r[7])
    ln   = crypto.decrypt_bytes_to_str_strict(r[8])
    em   = crypto.decrypt_bytes_to_str_strict(r[9])
    dobS = crypto.decrypt_bytes_to_str_strict(r[10])
    gt   = crypto.decrypt_bytes_to_str_strict(r[11])
    lon  = crypto.decrypt_number(r[12])
    lat  = crypto.decrypt_number(r[13])
    sq   = int(crypto.decrypt_number(r[14])) if r[14] is not None else None
    sa   = crypto.decrypt_bytes_to_str_strict(r[15]) if r[15] is not None else None

    return {
        "id": r[0],
        "gender" : gender,
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
        "is_info" : is_info,
    }


def fetch_person_decrypted_simple(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT person_id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, longitude, latitude 
                FROM T_People_Identity WHERE person_id=:person_id"""),
        return_result=True, params={"person_id": person_id}, bAngelmanResult=False
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
    t0 = time.perf_counter()
    logger.info("[V5][MAP] getRecordsPeople() start")

    t_db0 = time.perf_counter()
    rows = _run_query(
        text("""
            SELECT
                p.id,
                p.city,
                p.country,
                p.country_code,
                p.is_connected,
                p.age_years,
                i.firstname,
                i.lastname,
                i.genotype,
                i.longitude,
                i.latitude
            FROM T_People_Public   AS p
            INNER JOIN T_People_Identity AS i
                ON i.person_id = p.id
            ORDER BY p.id
        """),
        return_result=True,
        bAngelmanResult=False,
    )

    t_db1 = time.perf_counter()
    logger.info(
        "[V5][MAP] Private rows fetched: %d in %.3fs",
        len(rows),
        t_db1 - t_db0,
    )

    data = []

    decrypt_start = time.perf_counter()
    for row in rows:

        # Compatibilité selon la version de SQLAlchemy
        try:
            m = row._mapping   # SA 1.4+/2.0
        except AttributeError:
            m = dict(row)      # fallback

        pid = m["id"]
        city = m["city"]
        country = m["country"]
        country_code = m["country_code"]
        is_connected = m["is_connected"]
        age = m["age_years"]
        fn  = crypto.decrypt_bytes_to_str_strict(m["firstname"])
        ln  = crypto.decrypt_bytes_to_str_strict(m["lastname"])
        gt  = crypto.decrypt_bytes_to_str_strict(m["genotype"])
        long = crypto.decrypt_number(m["longitude"])
        lat = crypto.decrypt_number(m["latitude"])
   

        data.append({
            "id": pid,
            "firstname": fn,
            "lastname": ln,
            "city": city,                 # on prend la ville de la table publique
            "country": country,
            "country_code" : country_code,
            "is_connected" : is_connected,
            "age": age,                   # remap age_years -> age pour la sortie
            "genotype": gt,
            "longitude": long,
            "latitude": lat,
        })

    df = pd.DataFrame(data, columns=["id","firstname","lastname","city","country", "country_code", "is_connected", "age","genotype","longitude","latitude"])

    decrypt_end = time.perf_counter()
    logger.info(
        "[V5][MAP] DataFrame built: %d rows in %.3fs",
        len(df),
        decrypt_end - decrypt_start,
    )

    t1 = time.perf_counter()
    logger.info("[V5][MAP] getRecordsPeople() done in %.3fs", t1 - t0)

    return df

def getLang(session, idPeople: int) -> str | None:
    stmt = select(PeoplePublic.lang).where(PeoplePublic.id == idPeople)
    return session.execute(stmt).scalar_one_or_none()

def giveId(email_real):
    sha = crypto.email_sha256(email_real)
    row = _run_query(
        text("SELECT person_id FROM T_People_Identity WHERE email_sha = :sha LIMIT 1"),
        return_result=True,
        params={"sha": sha},
        bAngelmanResult=False
    )
    return int(row[0][0]) if row else None


def getQuestionSecrete(person_id: int) -> int | None:
    rows = _run_query(
        text("""SELECT secret_question FROM T_People_Identity WHERE person_id = :person_id LIMIT 1"""),
        params={"person_id": int(person_id)},
        return_result=True,
        bAngelmanResult=False
    )
    if not rows:
        return None
    sq_enc = rows[0][0]
    try:
        return int(crypto.decrypt_number(sq_enc)) if sq_enc is not None else None
    except Exception:
        return None


def _getListPaysFromDataSet():
    query = text("""SELECT DISTINCT country_code
                FROM T_People_Public
                WHERE status = 'active'
                ORDER BY country_code
                 """)
    rows = _run_query(query=query, return_result=True,bAngelmanResult=False)
    if(rows is None):
        return None
    country_codes = [row[0] for row in rows]
    try:
        return country_codes if country_codes is not None else None
    except Exception:
        return None
    
def getListPaysTranslate(locale: str = "fr"):
    listcountry_codes = _getListPaysFromDataSet()
    if not listcountry_codes:
        return []
    else:
        return countries_from_iso2_list_sorted_dict(listcountry_codes,locale=locale)
