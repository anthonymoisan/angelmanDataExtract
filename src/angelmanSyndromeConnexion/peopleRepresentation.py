import pandas as pd
import sys,os
import re
from sqlalchemy import bindparam,text
from datetime import date
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from tools.logger import setup_logger
from tools.utilsTools import _run_query,_insert_data
import tools.crypto_utils
import requests
from geopy.geocoders import Nominatim
import json
from angelmanSyndromeConnexion.geo_utils import get_city
from angelmanSyndromeConnexion.utils_image import coerce_to_date, detect_mime_from_bytes, normalize_mime,recompress_image
from angelmanSyndromeConnexion.error import AppError

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
        sha = tools.crypto_utils.email_sha256(email)  # 32 bytes, lookup déterministe
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
        return bool(tools.crypto_utils.verify_password_argon2(password, stored_hash_bytes))
    except Exception as e:
        logger.error("authenticate_email_password failed: %s", e, exc_info=True)
        return False


def authenticate_and_get_id(email: str, password: str) -> int | None:
    """
    Retourne l'ID si (email, mot de passe) est valide, sinon None.
    """
    try:
        sha = tools.crypto_utils.email_sha256(email)
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

        if tools.crypto_utils.verify_password_argon2(password, stored_hash_bytes):
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
    photo,           # bytes | None
    longitude,
    latitude,
    password,
    questionSecrete, # int 1..3
    reponseSecrete   # str (sera chiffrée)
):
    try:
        # -------- 1) Validations minimales --------
        if not isinstance(dateOfBirth, date):
            # Convertir côté appelant si nécessaire pour garantir un datetime.date
            raise TypeError("dateOfBirth doit être un datetime.date")

        dob = coerce_to_date(dateOfBirth)
        if dob > date.today():
            raise error.FutureDateError("dateOfBirth ne peut pas être dans le futur")

        # -------- 1bis) Photo : recompression et choix final --------
        photo_blob_final = None
        photo_mime_final = None

        if photo is not None:
            # Détection MIME robuste (indépendant de l'extension)
            detected_mime = detect_mime_from_bytes(photo)  # p.ex. "image/jpeg"
            src_mime = normalize_mime(detected_mime or "image/jpeg")
            if src_mime not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
                raise error.InvalidMimeTypeError(f"MIME non autorisé: {src_mime}")

            # Tenter une recompression (doit renvoyer (blob, mime) ou (None, None))
            try:
                new_blob, new_mime = recompress_image(photo)
            except Exception as e:
                logger.warning("Recompression échouée: %s", e, exc_info=True)
                new_blob, new_mime = None, None

            # Choisir la meilleure version (garder original si pas plus petit)
            if new_blob and len(new_blob) < len(photo):
                photo_blob_final = new_blob
                photo_mime_final = normalize_mime(new_mime or src_mime)
            else:
                photo_blob_final = photo
                photo_mime_final = src_mime

            # Contrôle de taille APRÈS recompression/fallback (contrainte DB)
            if len(photo_blob_final) > 4 * 1024 * 1024:
                raise error.PhotoTooLargeError("Photo > 4 MiB après recompression")
        else:
            photo_blob_final = None
            photo_mime_final = None  # cohérence avec vos CHECK

        # -------- 2) Dérivations applicatives --------
        age = age_years(dob)

        # Reverse géocoding best-effort (NE DOIT PAS planter l'insert)
        # NB: get_city attend (lat, lon)
        city_str = get_city(latitude, longitude) or ""  # fallback vide
        logger.info(city_str)

        # -------- 3) Chiffrement --------
        fn_enc  = tools.crypto_utils.encrypt_str(firstname)
        ln_enc  = tools.crypto_utils.encrypt_str(lastname)
        em_enc  = tools.crypto_utils.encrypt_str(emailAddress)
        dob_enc = tools.crypto_utils.encrypt_date_like(dob)
        gt_enc  = tools.crypto_utils.encrypt_str(genotype)
        ci_enc  = tools.crypto_utils.encrypt_str(city_str.strip())

        age_enc = tools.crypto_utils.encrypt_number(age)
        lon_enc = tools.crypto_utils.encrypt_number(longitude)
        lat_enc = tools.crypto_utils.encrypt_number(latitude)

        em_sha  = tools.crypto_utils.email_sha256(emailAddress)

        # --- Secret Q/A ---
        try:
            secret_q = int(questionSecrete)
        except Exception:
            raise error.ValidationError("questionSecrete doit être un entier 1..3")
        if secret_q not in (1, 2, 3):
            raise error.ValidationError("questionSecrete doit être 1, 2 ou 3")
        secret_que_enc = tools.crypto_utils.encrypt_number(secret_q)      # VARBINARY dans le schéma
        secret_ans_enc = tools.crypto_utils.encrypt_str(reponseSecrete)   # chiffrée

        # -------- 4) Hachage mot de passe (Argon2id) --------
        pwd_hash_bytes, pwd_meta = tools.crypto_utils.hash_password_argon2(password)
        pwd_meta_json = json.dumps(pwd_meta, separators=(",", ":"))
        pwd_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)  # DATETIME sans TZ

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
            "photo": photo_blob_final,          # bytes ou None
            "photo_mime": photo_mime_final,     # str ou None
            "city": ci_enc,
            "age": age_enc,
            "email_sha": em_sha,                # 32 bytes
            "pwd_hash": pwd_hash_bytes,         # bytes ($argon2id$… en bytes)
            "pwd_algo": "argon2id",
            "pwd_meta": pwd_meta_json,          # CHAÎNE JSON, castée côté SQL
            "pwd_updated_at": pwd_updated_at,
            "secret_q": secret_que_enc,         # chiffrée (VARBINARY)
            "secret_ans": secret_ans_enc,       # chiffrée (VARBINARY)
        }

        try:
            _run_query(sql, params=params)
        except IntegrityError as ie:
            # Clé unique sur email_sha
            raise error.DuplicateEmailError(
                "Un enregistrement avec cet email existe déjà"
            ) from ie

        # -------- 6) Retour indicatif --------
        lastRowId = _run_query(
            text("SELECT COUNT(*) FROM T_ASPeople"),
            return_result=True
        )
        return lastRowId[0][0]

    except error.AppError:
        raise
    except Exception:
        logger.error("Insert failed in T_ASPeople", exc_info=True)
        raise

def updateData(
    email_address : str,
    *,
    firstname=None,
    lastname=None,
    dateOfBirth=None,     # datetime.date | str ISO | None
    emailNewAddress=None,
    genotype=None,
    photo=None,           # bytes | None
    longitude=None,       # float | str | None
    latitude=None,        # float | str | None
    city=None,            # str | None
    password=None,        # str | None
    questionSecrete=None, # int | str | None (1..3)
    reponseSecrete=None,  # str | None
    delete_photo: bool=False,  # True => photo=NULL
):
    try:
        logger.info("Update a record")
        # -------- Helpers robustes --------
        def _to_float_or_none(v):
            if v in (None, "", "null"):
                return None
            try:
                return float(str(v).replace(",", "."))
            except Exception:
                return None

        def _to_int_or_none(v):
            if v in (None, "", "null"):
                return None
            try:
                return int(str(v).strip())
            except Exception:
                return None

        def _is_str_filled(v):
            return isinstance(v, str) and v.strip() != ""

        # -------- ID depuis l'email courant --------
        try:
            pid = giveId(email_address)
        except Exception:
            raise error.ValidationError("email address invalide")
        if pid is None:
            raise error.ValidationError("Utilisateur introuvable pour cet email")

        set_clauses = []
        params = {"id": pid}

        # -------- Normalisations d'entrée --------
        firstname       = firstname if _is_str_filled(firstname) else None
        lastname        = lastname  if _is_str_filled(lastname)  else None
        genotype        = genotype  if _is_str_filled(genotype)  else None
        city            = city      if _is_str_filled(city)      else None
        password        = password  if _is_str_filled(password)  else None
        emailNewAddress = emailNewAddress if _is_str_filled(emailNewAddress) else None
        reponseSecrete  = reponseSecrete  if _is_str_filled(reponseSecrete)  else None

        lon_val  = _to_float_or_none(longitude)
        lat_val  = _to_float_or_none(latitude)
        qsec_val = _to_int_or_none(questionSecrete)

        if dateOfBirth is not None:
            if isinstance(dateOfBirth, date):
                dob = dateOfBirth
            else:
                dob = coerce_to_date(dateOfBirth)
            if dob > date.today():
                raise error.FutureDateError("dateOfBirth ne peut pas être dans le futur")
        else:
            dob = None

        # -------- 1) Prénom / Nom / Génotype --------
        if firstname is not None:
            set_clauses.append("firstname = :fn")
            params["fn"] = tools.crypto_utils.encrypt_str(firstname)
        if lastname is not None:
            set_clauses.append("lastname = :ln")
            params["ln"] = tools.crypto_utils.encrypt_str(lastname)
        if genotype is not None:
            set_clauses.append("genotype = :gt")
            params["gt"] = tools.crypto_utils.encrypt_str(genotype)

        # -------- 2) Nouvel email --------
        if emailNewAddress is not None:
            em_enc = tools.crypto_utils.encrypt_str(emailNewAddress)
            em_sha = tools.crypto_utils.email_sha256(emailNewAddress)
            set_clauses += ["`emailAddress` = :em", "email_sha = :email_sha"]
            params["em"] = em_enc
            params["email_sha"] = em_sha

        # -------- 3) Date de naissance (+ âge) --------
        if dob is not None:
            age_val = age_years(dob)
            set_clauses += ["`dateOfBirth` = :dob", "age = :age"]
            params["dob"] = tools.crypto_utils.encrypt_date_like(dob)
            params["age"] = tools.crypto_utils.encrypt_number(age_val)

        # -------- 4) Long/Lat + ville --------
        lat_changed = (lat_val is not None)
        lon_changed = (lon_val is not None)
        if lon_changed:
            set_clauses.append("longitude = :lon")
            params["lon"] = tools.crypto_utils.encrypt_number(float(lon_val))
        if lat_changed:
            set_clauses.append("latitude = :lat")
            params["lat"] = tools.crypto_utils.encrypt_number(float(lat_val))

        if city is not None:
            set_clauses.append("city = :city")
            params["city"] = tools.crypto_utils.encrypt_str(city.strip())
        elif lat_changed or lon_changed:
            try:
                if (lat_val is not None) and (lon_val is not None):
                    city_str = get_city(lat_val, lon_val) or ""
                    set_clauses.append("city = :city")
                    params["city"] = tools.crypto_utils.encrypt_str(city_str.strip())
            except Exception as e:
                logger.warning("Reverse geocoding ignoré: %s", e)

        # -------- 5) Secret Q/A --------
        if qsec_val is not None:
            if qsec_val not in (1, 2, 3):
                raise error.ValidationError("questionSecrete doit être 1, 2 ou 3")
            set_clauses.append("secret_question = :secret_q")
            params["secret_q"] = tools.crypto_utils.encrypt_number(qsec_val)
        if reponseSecrete is not None:
            set_clauses.append("secret_answer = :secret_ans")
            params["secret_ans"] = tools.crypto_utils.encrypt_str(reponseSecrete)

        # -------- 6) Mot de passe --------
        if password is not None:
            if not isinstance(password, str) or not password:
                raise error.ValidationError("password ne doit pas être vide")
            pwd_hash_bytes, pwd_meta = tools.crypto_utils.hash_password_argon2(password)
            pwd_meta_json = json.dumps(pwd_meta, separators=(",", ":"))
            pwd_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            set_clauses.append("password_hash = :pwd_hash")
            set_clauses.append("password_algo = :pwd_algo")
            set_clauses.append("password_meta = CAST(:pwd_meta AS JSON)")
            set_clauses.append("password_updated_at = :pwd_updated_at")
            params.update({
                "pwd_hash": pwd_hash_bytes,
                "pwd_algo": "argon2id",
                "pwd_meta": pwd_meta_json,
                "pwd_updated_at": pwd_updated_at,
            })

        # -------- 7) Photo --------
        if delete_photo:
            set_clauses.append("photo = NULL") 
            set_clauses.append("photo_mime = NULL")
        elif photo is not None:
            detected_mime = detect_mime_from_bytes(photo)
            src_mime = normalize_mime(detected_mime or "image/jpeg")
            if src_mime not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
                raise error.InvalidMimeTypeError(f"MIME non autorisé: {src_mime}")

            try:
                new_blob, new_mime = recompress_image(photo)
            except Exception as e:
                logger.warning("Recompression échouée: %s", e, exc_info=True)
                new_blob, new_mime = None, None

            if new_blob and len(new_blob) < len(photo):
                photo_blob_final = new_blob
                photo_mime_final = normalize_mime(new_mime or src_mime)
            else:
                photo_blob_final = photo
                photo_mime_final = src_mime

            if len(photo_blob_final) > 4 * 1024 * 1024:
                raise error.PhotoTooLargeError("Photo > 4 MiB après recompression")

            set_clauses.append("photo = :photo")
            set_clauses.append("photo_mime = :photo_mime")
            params["photo"] = photo_blob_final
            params["photo_mime"] = photo_mime_final

        # -------- 8) Rien à faire ? --------
        if not set_clauses:
            logger.info("Aucun champ fourni pour update (id=%s)", pid)
            return 0

        # -------- 9) UPDATE --------
        sql = text(f"""
            UPDATE `T_ASPeople`
            SET {", ".join(set_clauses)}
            WHERE id = :id
            LIMIT 1
        """)
        try:
             _run_query(sql, params=params)
        except Exception:
            return 0
        return 1
    except error.AppError:
        return 0
    except Exception:
        logger.error("Update failed in T_ASPeople", exc_info=True)
        return 0

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
                       genotype, photo_mime, city, longitude, latitude, age, 
                       secret_question, secret_answer 
                FROM T_ASPeople WHERE id=:id"""),
        return_result=True, params={"id": person_id}
    )

    if not row:
        return None
    
    r = row[0]
    fn  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[1])
    ln  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[2])
    em  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[3])
    dob = tools.crypto_utils.decrypt_bytes_to_str_strict(r[4])
    gt  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[5])
    ci  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[7])
    long = tools.crypto_utils.decrypt_number(r[8])
    lat = tools.crypto_utils.decrypt_number(r[9])
    age = tools.crypto_utils.decrypt_number(r[10])
    secret_quest = (int)(tools.crypto_utils.decrypt_number(r[11]))
    secret_ans = tools.crypto_utils.decrypt_bytes_to_str_strict(r[12])

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
        "secret_question" : secret_quest,
        "secret_answer" : secret_ans,
    }

def fetch_person_decrypted_simple(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, city, longitude, latitude, age 
                FROM T_ASPeople WHERE id=:id"""),
        return_result=True, params={"id": person_id}
    )

    if not row:
        return None
    
    r = row[0]
    fn  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[1])
    ln  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[2])
    em  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[3])
    dob = tools.crypto_utils.decrypt_bytes_to_str_strict(r[4])
    gt  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[5])
    ci  = tools.crypto_utils.decrypt_bytes_to_str_strict(r[7])
    long = tools.crypto_utils.decrypt_number(r[8])
    lat = tools.crypto_utils.decrypt_number(r[9])
    age = tools.crypto_utils.decrypt_number(r[10])
    

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
        person = fetch_person_decrypted_simple(pid)   # ta fonction existante
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
    sha = tools.crypto_utils.email_sha256(email_real)
    row = _run_query(
        text("SELECT id FROM T_ASPeople WHERE email_sha = :sha LIMIT 1"),
        return_result=True,
        params={"sha": sha},
    )
    return int(row[0][0]) if row else None

from sqlalchemy import text
# ... import/engine/_run_query selon ton projet

def deleteDataById(person_id: int) -> int:
    """
    Supprime une personne par ID et renvoie le nombre de lignes supprimées (0 ou 1).
    Fallback: si l’enregistrement existait mais que rowcount est indéterminé,
    on renvoie 1.
    """
    pid = int(person_id)

    # 1) Vérifier existence
    exists_rows = _run_query(
        text("SELECT 1 FROM T_ASPeople WHERE id = :id LIMIT 1"),
        params={"id": pid},
        return_result=True
    )
    if not exists_rows or not exists_rows[0]:
        return 0  # rien à supprimer

    # 2) Supprimer
    res = _run_query(
        text("DELETE FROM T_ASPeople WHERE id = :id"),
        params={"id": pid}
    )

def getQuestionSecrete(person_id: int):
    """
    Retourne (question_code:int, reponse_claire:str) pour l'id donné,
    ou None si introuvable.
    """
    try:
        rows = _run_query(
            text("""
                SELECT secret_question
                FROM T_ASPeople
                WHERE id = :id
                LIMIT 1
            """),
            params={"id": int(person_id)},
            return_result=True,
        )
    except Exception as e:
        logger.exception("SQL error in getQuestionAndReponseSecrete(id=%s)", person_id)
        raise

    if not rows:
        return None

    sq_enc = rows[0][0]  # VARBINARY/bytes chiffrés
    # Déchiffre selon tes utilitaires
    try:
        secret_quest = int(tools.crypto_utils.decrypt_number(sq_enc))
    except Exception:
        # si decrypt_number renvoie déjà un int, enlève le int(...)
        secret_quest = tools.crypto_utils.decrypt_number(sq_enc)

    return secret_quest

# services/people.py (ou où se trouve votre logique métier)
import unicodedata
from sqlalchemy import text

# suppose que vous avez déjà :
# - _run_query(sql, params=..., return_result=True|False)
# - utils.email_sha256(...)
# - utils.decrypt_bytes_to_str_strict(...)
# - vos classes d'erreurs AppError / MissingFieldError si besoin

def _norm(s: str) -> str:
    """Normalise pour comparaison: trim, NFKC, lower()."""
    if s is None:
        return ""
    return unicodedata.normalize("NFKC", s).strip().lower()

def verifySecretAnswer(*, email: str | None = None, person_id: int | None = None, answer: str) -> bool:
    """
    Vérifie la réponse secrète.
    - On n'expose JAMAIS la réponse.
    - Retourne True si ça correspond, False sinon.
    - Si l'utilisateur n'existe pas: retourne False (évite l'énumération de comptes).
    """
    if not answer or not isinstance(answer, str):
        # on laisse l'API gérer les messages, ici on renvoie simplement False
        return False

    # Construction SQL selon l'identifiant fourni
    params = {}
    if email:
        sha = tools.crypto_utils.email_sha256(email)
        where = "email_sha = :sha"
        params["sha"] = sha
    elif person_id is not None:
        where = "id = :id"
        params["id"] = int(person_id)
    else:
        # pas d'identifiant -> échec silencieux
        return False

    rowset = _run_query(
        text(f"SELECT secret_answer FROM T_ASPeople WHERE {where} LIMIT 1"),
        params=params,
        return_result=True
    )
    if not rowset or not rowset[0]:
        # utilisateur introuvable -> renvoyer False (ne rien divulguer)
        return False

    enc_ans = rowset[0][0]  # VARBINARY chiffré
    try:
        stored = tools.crypto_utils.decrypt_bytes_to_str_strict(enc_ans)  # str
    except Exception:
        # si déchiffrement impossible -> on considère faux
        return False

    return _norm(answer) == _norm(stored)


