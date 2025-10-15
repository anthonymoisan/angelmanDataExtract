# src/angelmanSyndromeConnexion/peopleCreate.py
from __future__ import annotations
import json
from datetime import date, datetime, timezone
from sqlalchemy import text
from tools.logger import setup_logger
from tools.utilsTools import _run_query
import tools.crypto_utils as crypto
from angelmanSyndromeConnexion import error
from angelmanSyndromeConnexion.geo_utils import get_city
from angelmanSyndromeConnexion.utils_image import (
    coerce_to_date, detect_mime_from_bytes, normalize_mime, recompress_image
)

logger = setup_logger(debug=False)


def age_years(dob: date, on_date: date | None = None) -> int:
    if on_date is None:
        on_date = date.today()
    years = on_date.year - dob.year
    if (on_date.month, on_date.day) < (dob.month, dob.day):
        years -= 1
    return years


def insertData(
    firstname: str,
    lastname: str,
    emailAddress: str,
    dateOfBirth: date,
    genotype: str,
    photo: bytes | None,
    longitude: float,
    latitude: float,
    password: str,
    questionSecrete: int,   # 1..3
    reponseSecrete: str
) -> int:
    # 1) validations & normalisations
    if not isinstance(dateOfBirth, date):
        raise TypeError("dateOfBirth doit être un datetime.date")

    dob = coerce_to_date(dateOfBirth)
    if dob > date.today():
        raise error.FutureDateError("dateOfBirth ne peut pas être dans le futur")

    # 2) photo (recompression best-effort)
    photo_blob_final, photo_mime_final = None, None
    if photo is not None:
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

    # 3) dérivations
    age = age_years(dob)
    city_str = (get_city(latitude, longitude) or "").strip()

    # 4) chiffrement
    fn_enc  = crypto.encrypt_str(firstname)
    ln_enc  = crypto.encrypt_str(lastname)
    em_enc  = crypto.encrypt_str(emailAddress)
    dob_enc = crypto.encrypt_date_like(dob)
    gt_enc  = crypto.encrypt_str(genotype)
    ci_enc  = crypto.encrypt_str(city_str)

    age_enc = crypto.encrypt_number(age)
    lon_enc = crypto.encrypt_number(longitude)
    lat_enc = crypto.encrypt_number(latitude)

    em_sha  = crypto.email_sha256(emailAddress)

    # secret Q/A
    try:
        sq = int(questionSecrete)
    except Exception:
        raise error.ValidationError("questionSecrete doit être un entier 1..3")
    if sq not in (1, 2, 3):
        raise error.ValidationError("questionSecrete doit être 1, 2 ou 3")

    secret_q_enc = crypto.encrypt_number(sq)
    secret_a_enc = crypto.encrypt_str(reponseSecrete)

    # 5) hash mot de passe (Argon2id)
    pwd_hash_bytes, pwd_meta = crypto.hash_password_argon2(password)
    pwd_meta_json = json.dumps(pwd_meta, separators=(",", ":"))
    pwd_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # 6) INSERT
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
         :secret_q, :secret_a)
    """)
    params = {
        "fn": fn_enc, "ln": ln_enc, "em": em_enc, "dob": dob_enc, "gt": gt_enc,
        "lon": lon_enc, "lat": lat_enc, "photo": photo_blob_final, "photo_mime": photo_mime_final,
        "city": ci_enc, "age": age_enc, "email_sha": em_sha,
        "pwd_hash": pwd_hash_bytes, "pwd_algo": "argon2id",
        "pwd_meta": pwd_meta_json, "pwd_updated_at": pwd_updated_at,
        "secret_q": secret_q_enc, "secret_a": secret_a_enc,
    }
    try:
        _run_query(sql, params=params)
    except Exception as e:
        # Si vous avez une contrainte UNIQUE(email_sha), mappez 1062 -> DuplicateEmailError si utile
        raise

    # 7) retourne un indicateur simple (ex: COUNT, ou mieux: LAST_INSERT_ID si dispo)
    row = _run_query(text("SELECT LAST_INSERT_ID()"), return_result=True)
    return int(row[0][0]) if row and row[0][0] else 0
