# src/angelmanSyndromeConnexion/peopleUpdate.py
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
from angelmanSyndromeConnexion.peopleRead import giveId

logger = setup_logger(debug=False)


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


def age_years(dob: date, on_date: date | None = None) -> int:
    if on_date is None:
        on_date = date.today()
    years = on_date.year - dob.year
    if (on_date.month, on_date.day) < (dob.month, dob.day):
        years -= 1
    return years


def updateData(
    email_address : str,
    *,
    firstname=None,
    lastname=None,
    dateOfBirth=None,
    emailNewAddress=None,
    genotype=None,
    photo=None,
    longitude=None,
    latitude=None,
    city=None,
    password=None,
    questionSecrete=None,
    reponseSecrete=None,
    delete_photo: bool=False,
) -> int:
    logger.info("Update record for %s", email_address)

    # 1) resolve id from email
    try:
        pid = giveId(email_address)
    except Exception:
        raise error.ValidationError("email address invalide")
    if pid is None:
        raise error.ValidationError("Utilisateur introuvable pour cet email")

    set_clauses, params = [], {"id": pid}

    # 2) normalize inputs
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

    # 3) simple strings
    if firstname is not None:
        set_clauses.append("firstname = :fn")
        params["fn"] = crypto.encrypt_str(firstname)
    if lastname is not None:
        set_clauses.append("lastname = :ln")
        params["ln"] = crypto.encrypt_str(lastname)
    if genotype is not None:
        set_clauses.append("genotype = :gt")
        params["gt"] = crypto.encrypt_str(genotype)

    # 4) new email
    if emailNewAddress is not None:
        set_clauses += ["`emailAddress` = :em", "email_sha = :email_sha"]
        params["em"] = crypto.encrypt_str(emailNewAddress)
        params["email_sha"] = crypto.email_sha256(emailNewAddress)

    # 5) date + age
    if dob is not None:
        set_clauses += ["`dateOfBirth` = :dob", "age = :age"]
        params["dob"] = crypto.encrypt_date_like(dob)
        params["age"] = crypto.encrypt_number(age_years(dob))

    # 6) lon/lat + city (auto)
    lat_changed = (lat_val is not None)
    lon_changed = (lon_val is not None)
    if lon_changed:
        set_clauses.append("longitude = :lon")
        params["lon"] = crypto.encrypt_number(float(lon_val))
    if lat_changed:
        set_clauses.append("latitude = :lat")
        params["lat"] = crypto.encrypt_number(float(lat_val))

    if city is not None:
        set_clauses.append("city = :city")
        params["city"] = crypto.encrypt_str(city.strip())
    elif lat_changed or lon_changed:
        try:
            if (lat_val is not None) and (lon_val is not None):
                city_str = get_city(lat_val, lon_val) or ""
                set_clauses.append("city = :city")
                params["city"] = crypto.encrypt_str(city_str.strip())
        except Exception as e:
            logger.warning("Reverse geocoding ignoré: %s", e)

    # 7) secret Q/A
    if qsec_val is not None:
        if qsec_val not in (1, 2, 3):
            raise error.ValidationError("questionSecrete doit être 1, 2 ou 3")
        set_clauses.append("secret_question = :secret_q")
        params["secret_q"] = crypto.encrypt_number(qsec_val)
    if reponseSecrete is not None:
        set_clauses.append("secret_answer = :secret_ans")
        params["secret_ans"] = crypto.encrypt_str(reponseSecrete)

    # 8) password
    if password is not None:
        pwd_hash_bytes, pwd_meta = crypto.hash_password_argon2(password)
        pwd_meta_json = json.dumps(pwd_meta, separators=(",", ":"))
        pwd_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        set_clauses += [
            "password_hash = :pwd_hash",
            "password_algo = :pwd_algo",
            "password_meta = CAST(:pwd_meta AS JSON)",
            "password_updated_at = :pwd_updated_at",
        ]
        params.update({
            "pwd_hash": pwd_hash_bytes,
            "pwd_algo": "argon2id",
            "pwd_meta": pwd_meta_json,
            "pwd_updated_at": pwd_updated_at,
        })

    # 9) photo
    if delete_photo:
        set_clauses += ["photo = NULL", "photo_mime = NULL"]
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

        set_clauses += ["photo = :photo", "photo_mime = :photo_mime"]
        params["photo"] = photo_blob_final
        params["photo_mime"] = photo_mime_final

    if not set_clauses:
        logger.info("Aucun champ fourni pour update (id=%s)", pid)
        return 0

    sql = text(f"""
        UPDATE `T_ASPeople`
        SET {", ".join(set_clauses)}
        WHERE id = :id
        LIMIT 1
    """)
    try:
        _run_query(sql, params=params)
    except Exception:
        logger.exception("Update failed")
        return 0
    return 1
