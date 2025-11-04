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
from angelmanSyndromeConnexion.peopleRead import giveId, fetch_person_decrypted_simple

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
    dateOfBirth=None,        # date | str ISO
    emailNewAddress=None,
    genotype=None,
    photo=None,              # bytes
    longitude=None,          # float|str
    latitude=None,           # float|str
    city=None,               # str (CLAIR → table publique)
    password=None,           # str (Argon2)
    questionSecrete=None,    # 1..3
    reponseSecrete=None,     # str
    delete_photo: bool=False
) -> int:
    """
    Met à jour T_People_Identity (données chiffrées) ET T_People_Public (claires).
    Retourne 1 si quelque chose a été modifié, 0 sinon.
    """
    logger.info("Update (2-tables) for %s", email_address)

    # 1) Résoudre l'id depuis l'email (via email_sha dans la table identity)
    pid = giveId(email_address)
    if pid is None:
        raise error.ValidationError("Utilisateur introuvable pour cet email")

    # 2) Normalisations
    firstname       = firstname if _is_str_filled(firstname) else None
    lastname        = lastname  if _is_str_filled(lastname)  else None
    genotype        = genotype  if _is_str_filled(genotype)  else None
    password        = password  if _is_str_filled(password)  else None
    emailNewAddress = emailNewAddress if _is_str_filled(emailNewAddress) else None
    reponseSecrete  = reponseSecrete  if _is_str_filled(reponseSecrete)  else None
    city            = city if _is_str_filled(city) else None
    lon_val  = _to_float_or_none(longitude)
    lat_val  = _to_float_or_none(latitude)
    qsec_val = _to_int_or_none(questionSecrete)

    if dateOfBirth is not None:
        dob = coerce_to_date(dateOfBirth) if not isinstance(dateOfBirth, date) else dateOfBirth
        if dob > date.today():
            raise error.FutureDateError("dateOfBirth ne peut pas être dans le futur")
    else:
        dob = None

    # 3) Construire UPDATE pour la table privée (Identity)
    ident_sets = []
    ident_params = {"id": pid}

    if firstname is not None:
        ident_sets.append("firstname = :fn")
        ident_params["fn"] = crypto.encrypt_str(firstname)

    if lastname is not None:
        ident_sets.append("lastname = :ln")
        ident_params["ln"] = crypto.encrypt_str(lastname)

    if genotype is not None:
        ident_sets.append("genotype = :gt")
        ident_params["gt"] = crypto.encrypt_str(genotype)

    # email → chiffré + sha
    if emailNewAddress is not None:
        ident_sets += ["emailAddress = :em", "email_sha = :email_sha"]
        ident_params["em"] = crypto.encrypt_str(emailNewAddress)
        ident_params["email_sha"] = crypto.email_sha256(emailNewAddress)

    # date de naissance (chiffrée)
    age_new: int | None = None
    if dob is not None:
        ident_sets.append("dateOfBirth = :dob")
        ident_params["dob"] = crypto.encrypt_date_like(dob)
        age_new = age_years(dob)  # servira à MAJ table publique

    # lon/lat (chiffrés)
    lat_changed = lat_val is not None
    lon_changed = lon_val is not None
    if lon_changed:
        ident_sets.append("longitude = :lon")
        ident_params["lon"] = crypto.encrypt_number(float(lon_val))
    if lat_changed:
        ident_sets.append("latitude = :lat")
        ident_params["lat"] = crypto.encrypt_number(float(lat_val))

    # secret Q/A
    if qsec_val is not None:
        if qsec_val not in (1, 2, 3):
            raise error.ValidationError("questionSecrete doit être 1, 2 ou 3")
        ident_sets.append("secret_question = :secret_q")
        ident_params["secret_q"] = crypto.encrypt_number(qsec_val)
    if reponseSecrete is not None:
        ident_sets.append("secret_answer = :secret_ans")
        ident_params["secret_ans"] = crypto.encrypt_str(reponseSecrete)

    # password (Argon2)
    if password is not None:
        pwd_hash_bytes, pwd_meta = crypto.hash_password_argon2(password)
        ident_sets += [
            "password_hash = :pwd_hash",
            "password_algo = :pwd_algo",
            "password_meta = CAST(:pwd_meta AS JSON)",
            "password_updated_at = :pwd_updated_at",
        ]
        ident_params.update({
            "pwd_hash": pwd_hash_bytes,
            "pwd_algo": "argon2id",
            "pwd_meta": json.dumps(pwd_meta, separators=(",", ":")),
            "pwd_updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
        })

    # photo
    if delete_photo:
        ident_sets += ["photo = NULL", "photo_mime = NULL"]
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

        ident_sets += ["photo = :photo", "photo_mime = :photo_mime"]
        ident_params["photo"] = photo_blob_final
        ident_params["photo_mime"] = photo_mime_final

    # 4) Construire UPDATE pour la table publique (Public)
    public_sets = []
    public_params = {"id": pid}

    # city (clair). Si non fourni et lon/lat modifiés → reverse geocoding best-effort
    if city is not None:
        public_sets.append("city = :city")
        public_params["city"] = city.strip()
    elif lat_changed or lon_changed:
        try:
            if (lat_val is not None) and (lon_val is not None):
                city_str = get_city(lat_val, lon_val) or ""
                public_sets.append("city = :city")
                public_params["city"] = city_str.strip()
        except Exception as e:
            logger.warning("Reverse geocoding ignoré: %s", e)

    # age_years (clair)
    if age_new is not None:
        public_sets.append("age_years = :age_years")
        public_params["age_years"] = int(age_new)

    if firstname is not None and lastname is not None:
        public_sets.append("pseudo = :pseudo")
        public_params["pseudo"] = f"{firstname} {lastname[0]}."
    elif firstname is not None:
        #lastNewName is None
        person = fetch_person_decrypted_simple(pid)
        public_sets.append("pseudo = :pseudo")
        valueLastName = person["lastname"][0]
        public_params["pseudo"] = f"{firstname} {valueLastName}."
    elif lastname is not None:
        person = fetch_person_decrypted_simple(pid)
        valueFirstName = person["firstname"]
        public_sets.append("pseudo = :pseudo")
        public_params["pseudo"] = f"{valueFirstName} {lastname[0]}."
    # 5) Exécutions SQL (seulement s’il y a quelque chose à modifier)
    affected = 0

    if ident_sets:
        sql_ident = text(f"""
            UPDATE T_People_Identity
               SET {", ".join(ident_sets)}
             WHERE person_id = :id
             LIMIT 1
        """)
        try:
            _run_query(sql_ident, params=ident_params,bAngelmanResult=False)
            affected = 1
        except Exception:
            logger.exception("Update failed (Identity)")
            # on continue pour tenter la partie publique si souhaité, sinon return 0
            return 0

    if public_sets:
        sql_public = text(f"""
            UPDATE T_People_Public
               SET {", ".join(public_sets)}
             WHERE id = :id
             LIMIT 1
        """)
        try:
            _run_query(sql_public, params=public_params,bAngelmanResult=False)
            affected = 1
        except Exception:
            logger.exception("Update failed (Public)")
            return 0

    if not ident_sets and not public_sets:
        logger.info("Aucun champ fourni pour update (id=%s)", pid)
        return 0

    return affected