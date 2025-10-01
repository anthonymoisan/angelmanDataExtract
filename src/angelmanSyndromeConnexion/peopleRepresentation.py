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

# Set up logger
logger = setup_logger(debug=False)


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

def getCity(longitude, latitude):
    geolocator = Nominatim(user_agent="ASConnect")  # mettez un UA parlant
    location = geolocator.reverse((latitude,longitude), language="fr")
    ville = location.raw.get("address", {}).get("city") or \
            location.raw.get("address", {}).get("town") or \
            location.raw.get("address", {}).get("village")
    return ville


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
        # 0) validations simples de présence
        if not firstname or not lastname:
            raise error.ValidationError("Firstname et Lastname sont requis")
        if not isinstance(questionSecrete, int) or not (1 <= questionSecrete <= 3):
            raise error.ValidationError("questionSecrete doit être un entier entre 1 et 3")
        if not isinstance(reponseSecrete, str) or not reponseSecrete.strip():
            raise error.ValidationError("La réponse à la question secrète est requise")
        if not password or not isinstance(password, str):
            raise error.ValidationError("Le mot de passe est requis")

        # 1) validations applicatives existantes
        if not isinstance(dateOfBirth, date):
            raise TypeError("dateOfBirth doit être un datetime.date")
        dob = utils.coerce_to_date(dateOfBirth)
        if dob > date.today():
            raise error.FutureDateError("dateOfBirth ne peut pas être dans le futur")
        if photo is not None and len(photo) > 4 * 1024 * 1024:
            raise error.PhotoTooLargeError("Photo > 4 MiB")

        detected   = utils.detect_mime_from_bytes(photo) if photo else None
        photo_mime = utils.normalize_mime(detected or "image/jpeg") if photo else None
        if photo and photo_mime not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
            raise error.InvalidMimeTypeError(f"MIME non autorisé: {photo_mime}")

        # 1.b) Politique mot de passe (min 8, 1 maj, 1 chiffre, 1 spécial)
        pwd = password.strip()
        has_min = len(pwd) >= 8
        has_upper = bool(re.search(r"[A-Z]", pwd))
        has_digit = bool(re.search(r"\d", pwd))
        has_spec  = bool(re.search(r'[!@#\$%^&*(),.?":{}|<>_\-+=~;\\/\[\]]', pwd))
        if not (has_min and has_upper and has_digit and has_spec):
            raise error.ValidationError(
                "Mot de passe trop faible (Min.8, 1 majuscule, 1 chiffre, 1 caractère spécial)"
            )

        # 2) dérivation champs calculés
        age = age_years(dob)
        city = getCity(longitude, latitude)
        logger.info(city)

        # 3) chiffrement / hachage
        fn_enc  = utils.encrypt_str(firstname)
        ln_enc  = utils.encrypt_str(lastname)
        em_enc  = utils.encrypt_str(emailAddress)      # bytes chiffrés
        dob_enc = utils.encrypt_date_like(dob)
        gt_enc  = utils.encrypt_str(genotype)
        ci_enc  = utils.encrypt_str((city or "").strip())
        age_enc = utils.encrypt_number(age)
        lon_enc = utils.encrypt_number(longitude)
        lat_enc = utils.encrypt_number(latitude)

        # hachage déterministe pour unicité
        em_sha  = utils.email_sha256(emailAddress)     # BINARY(32)

        # mot de passe : Argon2id (format PHC en bytes) + meta JSON
        # -> adapte si ton util renvoie autre chose
        pwd_hash_bytes, pwd_meta = utils.hash_password_argon2(pwd)
        pwd_algo = "argon2id"
        pwd_meta_json = json.dumps(pwd_meta, separators=(",", ":"))
        pwd_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)  # TIMESTAMP (naive UTC)

        # question secrète (entier) + réponse secrète chiffrée
        secret_q = int(questionSecrete)
        secret_ans_enc = utils.encrypt_str(reponseSecrete.strip())

        # 4) préparation DataFrame
        rowData = {
            "firstname":      [fn_enc],
            "lastname":       [ln_enc],
            "emailAddress":   [em_enc],
            "dateOfBirth":    [dob_enc],
            "genotype":       [gt_enc],
            "longitude":      [lon_enc],
            "latitude":       [lat_enc],
            "photo":          [photo],
            "photo_mime":     [photo_mime],
            "city":           [ci_enc],
            "age":            [age_enc],
            "email_sha":      [em_sha],

            # Nouveaux champs auth
            "password_hash":      [pwd_hash_bytes],
            "password_algo":      [pwd_algo],
            "password_meta":      [pwd_meta_json],
            "password_updated_at":[pwd_updated_at],   # TIMESTAMP

            "secret_question":    [secret_q],         # TINYINT UNSIGNED
            "secret_answer":      [secret_ans_enc],   # VARBINARY (chiffré)
        }

        df = pd.DataFrame.from_dict(rowData)

        # 5) insertion
        try:
            _insert_data(df, "T_ASPeople", if_exists="append")
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
        paramsSQL={"id": person_id},
    )

    if not rows:
        return None, None
    photo, mime = rows[0]
    return photo, mime or "image/jpeg"
  
def get_email(person_id: int) -> str | None:
    row = _run_query(
        text("""SELECT emailAddress FROM T_ASPeople WHERE id=:id"""),
        return_result=True, paramsSQL={"id": person_id}
    )
    return str(utils.decrypt_bytes_to_str_strict(row[0][0]))

def get_email2(firstName,lastName, age, city):
    row = _run_query(
        text("""SELECT emailAddress FROM T_ASPeople WHERE firstname=:firstname AND lastname=:lastname AND age:=age AND city:=city"""),
        return_result=True, paramsSQL={"firstname": firstName, "lastname" : lastName, age:"age", city:"city"}
    )
    return str(utils.decrypt_bytes_to_str_strict(row[0][0]))


def fetch_person_decrypted(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, city, longitude, latitude, age
                FROM T_ASPeople WHERE id=:id"""),
        return_result=True, paramsSQL={"id": person_id}
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
        paramsSQL={"sha": sha},
    )
    return int(row[0][0]) if row else None


    