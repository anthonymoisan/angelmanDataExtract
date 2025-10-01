from . import utils
from . import error
import pandas as pd
import sys,os
import re
from sqlalchemy import bindparam,text
from datetime import date
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger
from utilsTools import _run_query,_insert_data
import requests
from geopy.geocoders import Nominatim
import json
from .geo_utils import get_city

# Set up logger
logger = setup_logger(debug=False)

def _to_bytes_phc(x) -> bytes:
    """S'assure que le hash PHC est bien en bytes pour utils.verify_password_argon2."""
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    # parfois certains drivers retournent déjà une str
    return str(x).encode("utf-8", "strict")


def authenticate_email_password(email: str, password: str) -> bool:
    """
    Retourne True si (email, mot de passe) est valide, sinon False.
    """
    try:
        sha = utils.email_sha256(email)  # 32 bytes, lookup déterministe
        row = _run_query(
            text("""
                SELECT password_hash
                FROM T_ASPeople
                WHERE email_sha = :sha
                LIMIT 1
            """),
            return_result=True,
            params={"sha": sha},
        )
        if not row:
            return False

        stored_hash_bytes = _to_bytes_phc(row[0][0])
        return bool(utils.verify_password_argon2(password, stored_hash_bytes))
    except Exception as e:
        logger.error("authenticate_email_password failed: %s", e, exc_info=True)
        return False


def authenticate_and_get_id(email: str, password: str) -> int | None:
    """
    Retourne l'ID si (email, mot de passe) est valide, sinon None.
    """
    try:
        sha = utils.email_sha256(email)
        row = _run_query(
            text("""
                SELECT id, password_hash
                FROM T_ASPeople
                WHERE email_sha = :sha
                LIMIT 1
            """),
            return_result=True,
            params={"sha": sha},
        )
        if not row:
            return None

        pid, pwd_hash_db = row[0]
        stored_hash_bytes = _to_bytes_phc(pwd_hash_db)

        if utils.verify_password_argon2(password, stored_hash_bytes):
            return int(pid)
        return None
    except Exception as e:
        logger.error("authenticate_and_get_id failed: %s", e, exc_info=True)
        return None

def age_years(dob, on_date=None):
    """
    dob : date ou str ISO 'YYYY-MM-DD'
    on_date : date de référence (par défaut: aujourd'hui)
    """
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)  # '1990-05-12'
    if on_date is None:
        on_date = date.today()

    years = on_date.year - dob.year
    # Si l'anniversaire n'est pas encore passé cette année, retirer 1
    if (on_date.month, on_date.day) < (dob.month, dob.day):
        years -= 1
    return years


def insertData(
    firstname,
    lastname,
    emailAddress,
    dateOfBirth,
    genotype,
    photo,
    longitude,
    latitude,
    password,
    questionSecrete,   # int 1..3
    reponseSecrete     # str (sera chiffrée)
):
    try:
        # -------- 1) Validations minimales --------
        if not isinstance(dateOfBirth, date):
            # Si on te passe un str, convertis-le côté appelant avant d'arriver ici
            raise TypeError("dateOfBirth doit être un datetime.date")

        dob = utils.coerce_to_date(dateOfBirth)
        if dob > date.today():
            raise error.FutureDateError("dateOfBirth ne peut pas être dans le futur")

        if photo is not None:
            if len(photo) > 4 * 1024 * 1024:
                raise error.PhotoTooLargeError("Photo > 4 MiB")
            detected = utils.detect_mime_from_bytes(photo)
            photo_mime = utils.normalize_mime(detected or "image/jpeg")
            if photo_mime not in {"image/jpeg","image/jpg","image/png","image/webp"}:
                raise error.InvalidMimeTypeError(f"MIME non autorisé: {photo_mime}")
        else:
            photo_mime = None  # doit matcher la contrainte: photo NULL => photo_mime NULL

        # -------- 2) Dérivations applicatives --------
        age = age_years(dob)

        # Reverse géocoding best-effort (NE DOIT PAS planter l'insert)
        # NB: get_city attend (lat, lon)
        city_str = get_city(latitude, longitude) or ""  # fallback vide

        logger.info(city_str)

        # -------- 3) Chiffrement --------
        fn_enc  = utils.encrypt_str(firstname)
        ln_enc  = utils.encrypt_str(lastname)
        em_enc  = utils.encrypt_str(emailAddress)
        dob_enc = utils.encrypt_date_like(dob)
        gt_enc  = utils.encrypt_str(genotype)
        ci_enc  = utils.encrypt_str(city_str.strip())

        age_enc = utils.encrypt_number(age)
        lon_enc = utils.encrypt_number(longitude)
        lat_enc = utils.encrypt_number(latitude)

        em_sha  = utils.email_sha256(emailAddress)

        # --- Secret Q/A ---
        # questionSecrete: entier 1..3 (assuré côté appelant)
        try:
            secret_q = int(questionSecrete)
        except Exception:
            raise error.ValidationError("questionSecrete doit être un entier 1..3")
        if secret_q not in (1, 2, 3):
            raise error.ValidationError("questionSecrete doit être 1, 2 ou 3")
        secret_ans_enc = utils.encrypt_str(reponseSecrete)

        # -------- 4) Hachage mot de passe (Argon2id) --------
        # utils.hash_password_argon2(password) -> (hash_bytes, meta_dict)
        pwd_hash_bytes, pwd_meta = utils.hash_password_argon2(password)
        pwd_meta_json = json.dumps(pwd_meta, separators=(",", ":"))
        pwd_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)  # DATETIME sans TZ

        # Cohérence photo / mime (contrainte SQL):
        if photo is None:
            photo_mime = None

        # -------- 5) INSERT SQL paramétré --------
        sql = text("""
        INSERT INTO `T_ASPeople`
        (firstname, lastname, `emailAddress`, `dateOfBirth`, genotype,
         longitude, latitude, photo, photo_mime, city, age, email_sha,
         password_hash, password_algo, password_meta, password_updated_at,
         secret_question, secret_answer)
        VALUES
        (:fn, :ln, :em, :dob, :gt,
         :lon, :lat, :photo, :photo_mime, :city, :age, :email_sha,
         :pwd_hash, :pwd_algo, CAST(:pwd_meta AS JSON), :pwd_updated_at,
         :secret_q, :secret_ans)
        """)

        params = {
            "fn": fn_enc,
            "ln": ln_enc,
            "em": em_enc,
            "dob": dob_enc,
            "gt": gt_enc,
            "lon": lon_enc,
            "lat": lat_enc,
            "photo": photo,               # bytes ou None
            "photo_mime": photo_mime,     # str ou None
            "city": ci_enc,
            "age": age_enc,
            "email_sha": em_sha,          # 32 bytes
            "pwd_hash": pwd_hash_bytes,   # bytes (la string $argon2id$… en bytes)
            "pwd_algo": "argon2id",
            "pwd_meta": pwd_meta_json,    # CHAÎNE JSON, castée côté SQL
            "pwd_updated_at": pwd_updated_at,
            "secret_q": secret_q,
            "secret_ans": secret_ans_enc,
        }

        # 5) insertion
        try:
            # Exécution
            _run_query(sql, params=params)
        except IntegrityError as ie:
            # clé unique sur email_sha
            raise error.DuplicateEmailError(
                "Un enregistrement avec cet email existe déjà"
            ) from ie

        # 6) retourner un indicateur (ex: nb total ou id)
        lastRowId = _run_query(
            text("SELECT COUNT(*) FROM T_ASPeople"),
            return_result=True
        )
        return lastRowId[0][0]

    except error.AppError as e:
        raise
    except Exception:
        logger.error("Insert failed in T_ASPeople", exc_info=True)
        raise


def fetch_photo(person_id: int):
    rows = _run_query(
        text("SELECT photo, photo_mime FROM T_ASPeople WHERE id=:id"),
        return_result=True,
        params={"id": person_id},
    )

    if not rows:
        return None, None
    photo, mime = rows[0]
    return photo, mime or "image/jpeg"


def fetch_person_decrypted(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, city, longitude, latitude, age
                FROM T_ASPeople WHERE id=:id"""),
        return_result=True, params={"id": person_id}
    )

    if not row:
        return None
    
    r = row[0]
    fn  = utils.decrypt_bytes_to_str_strict(r[1])
    ln  = utils.decrypt_bytes_to_str_strict(r[2])
    em  = utils.decrypt_bytes_to_str_strict(r[3])
    dob = utils.decrypt_bytes_to_str_strict(r[4])
    gt  = utils.decrypt_bytes_to_str_strict(r[5])
    ci  = utils.decrypt_bytes_to_str_strict(r[7])
    long = utils.decrypt_number(r[8])
    lat = utils.decrypt_number(r[9])
    age = utils.decrypt_number(r[10])

    return {
        "id": r[0],
        "firstname": fn,
        "lastname": ln,
        "email": em,
        "dateOfBirth": date.fromisoformat(dob) if dob else None,
        "genotype": gt,
        "photo_mime": r[6],
        "city" : ci,
        "age" : age,
        "longitude" : long,
        "latitude" : lat,
    }

def getRecordsPeople():
    data = []
    #Only need City, Id, Firstname, LastName, Genotype
    rows = _run_query(
        text("SELECT id FROM T_ASPeople ORDER BY id"),
        return_result=True)

    for (pid,) in rows:               # chaque row est un tuple (id,)
        person = fetch_person_decrypted(pid)   # ta fonction existante
        if not person:
            continue
        data.append({
            "id": pid,
            "firstname": person["firstname"],
            "lastname": person["lastname"],
            "city": person["city"],
            "age" : person["age"],
            "genotype" : person["genotype"],
            "longitude" : person["longitude"],
            "latitude" : person["latitude"]
        })
    df = pd.DataFrame(data, columns=["id","firstname","lastname","city","age","genotype","longitude","latitude"])
    return df
    
def giveId(email_real):
    sha = utils.email_sha256(email_real)
    row = _run_query(
        text("SELECT id FROM T_ASPeople WHERE email_sha = :sha LIMIT 1"),
        return_result=True,
        params={"sha": sha},
    )
    return int(row[0][0]) if row else None


    