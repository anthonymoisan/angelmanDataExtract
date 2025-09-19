import sys, os
from tkinter import Image
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from utilsTools import send_email_alert, _run_query,_insert_data
import time
import logging
from logger import setup_logger
import pandas as pd
from cryptography.fernet import Fernet
from configparser import ConfigParser
from sqlalchemy import bindparam,text
from datetime import date
from pathlib import Path
from datetime import datetime, timezone
import io
import hashlib
from sqlalchemy.exc import IntegrityError
from error import AppError,BadDateFormatError,DuplicateEmailError,FutureDateError,InvalidMimeTypeError, PhotoTooLargeError

# Set up logger
logger = setup_logger(debug=False)
wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../angelman_viz_keys/Config4.ini"
config.read(filePath)
key = config['CleChiffrement']['KEY']

cipher = Fernet(key)

# --- helpers ---
def norm_email(e: str) -> str:
    return e.strip().lower()

def email_sha256(e: str) -> bytes:
    return hashlib.sha256(norm_email(e).encode("utf-8")).digest()

def encrypt_str(s: str) -> bytes:
    return cipher.encrypt(s.encode("utf-8"))  # -> bytes pour VARBINARY

def encrypt_date_like(d) -> bytes:
    # accepte date / datetime / pandas.Timestamp / str
    from datetime import date, datetime
    import pandas as pd

    if isinstance(d, pd.Timestamp):
        d = d.date()
    elif isinstance(d, datetime):
        d = d.date()
    elif isinstance(d, str):
        # garde juste la partie date si "YYYY-MM-DDTHH:MM:SS"
        d = d.split('T')[0].split(' ')[0]
        return cipher.encrypt(d.encode('utf-8'))
    elif isinstance(d, date):
        pass
    else:
        raise TypeError("Type de date non supporté")

    return cipher.encrypt(d.isoformat().encode('utf-8'))


def createTable(sql_script):
    script_path = os.path.join(os.path.dirname(__file__), "angelmanSyndromeConnexion/SQL", sql_script)
    with open(script_path, "r", encoding="utf-8") as file:
        logger.info("--- Create Table.")
        _run_query(file.read())


def coerce_to_date(d) -> date:
    # déjà une date (pas datetime)
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    # datetime -> date
    if isinstance(d, datetime):
        return d.date()
    # pandas Timestamp
    if isinstance(d, pd.Timestamp):
        return d.date()
    # numpy datetime64
    if isinstance(d, np.datetime64):
        return pd.to_datetime(d).date()
    # string "YYYY-MM-DD" ou "YYYY-MM-DDTHH:MM:SS"
    if isinstance(d, str):
        s = d.strip()
        try:
            return date.fromisoformat(s.split("T")[0].split(" ")[0])
        except Exception:
            # tente quelques formats courants si besoin
            for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    pass
            raise BadDateFormatError(f"Format de date invalide: {d!r}")
    raise TypeError(f"Type de date non supporté: {type(d)}")

def insertData(firstname, lastname, emailAddress, dateOfBirth, genotype, photo, city):

    try:
            
        # 1) validations applicatives minimum
        if not isinstance(dateOfBirth, date):
            raise TypeError("dateOfBirth doit être un datetime.date")
        dob = coerce_to_date(dateOfBirth)
        if dob > date.today():
            raise FutureDateError("dateOfBirth ne peut pas être dans le futur")
        if photo is not None and len(photo) > 4 * 1024 * 1024:
            raise PhotoTooLargeError("Photo > 4 MiB")
        
        detected = detect_mime_from_bytes(photo) if photo else None
        photo_mime = normalize_mime(detected or "image/jpeg") if photo else None
        if photo and photo_mime not in {"image/jpeg","image/jpg","image/png","image/webp"}:
            raise InvalidMimeTypeError(f"MIME non autorisé: {photo_mime}")

        # 2) chiffrement des champs
        fn_enc   = encrypt_str(firstname)
        ln_enc   = encrypt_str(lastname)
        em_enc   = encrypt_str(emailAddress)  # bytes
        dob_enc  = encrypt_date_like(dateOfBirth)
        gt_enc   = encrypt_str(genotype)
        ci_enc = encrypt_str(city.strip()) if isinstance(city, str) and city.strip() else None

        # hash déterministe pour unicité
        em_sha  = email_sha256(emailAddress)

        rowData = {
            "firstname": [fn_enc],
            "lastname": [ln_enc],
            "emailAddress": [em_enc],
            "dateOfBirth": [dob_enc],
            "genotype" : [gt_enc],
            "photo": [photo],
            "photo_mime": [photo_mime], 
            "city": [ci_enc],
            "email_sha" : [em_sha]
        }

        df = pd.DataFrame.from_dict(rowData)
        
        try:
            _insert_data(df, "T_ASPeople", if_exists="append")
        except IntegrityError as ie:
            # MySQL duplicate unique key -> 1062
            # selon driver, on peut aussi tester: if "1062" in str(ie.orig)
            raise DuplicateEmailError("Un enregistrement avec cet email existe déjà") from ie

        lastRowId = _run_query(
        text("SELECT COUNT(*) FROM T_ASPeople"),
        return_result=True)

        return lastRowId[0][0]
    except AppError as e:
        raise(e)
    except Exception:
        logger.error("Insert failed in T_ASPeople")
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


def dropTable():
    sql = "DROP TABLE T_ASPeople"
    _run_query(sql)
   
CANONICAL_MIME = {
    "JPEG": "image/jpeg",
    "PNG":  "image/png",
    "WEBP": "image/webp",
}

ALIASES = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
}

def detect_mime_from_bytes(b: bytes) -> str | None:
    try:
        with Image.open(io.BytesIO(b)) as im:
            fmt = (im.format or "").upper()
        return CANONICAL_MIME.get(fmt)
    except Exception:
        return None

def normalize_mime(mime: str | None) -> str | None:
    if mime is None:
        return None
    return ALIASES.get(mime, mime)

# Déchiffrement bytes -> str (UTF-8)
def decrypt_bytes_to_str(b: bytes | memoryview | None) -> str | None:
    if b is None:
        return None
    if isinstance(b, memoryview):
        b = b.tobytes()
    return cipher.decrypt(b).decode("utf-8")

def fetch_person_decrypted(person_id: int) -> dict | None:
    row = _run_query(
        text("""SELECT id, firstname, lastname, emailAddress, dateOfBirth,
                       genotype, photo_mime, city
                FROM T_ASPeople WHERE id=:id"""),
        return_result=True, paramsSQL={"id": person_id}
    )

    if not row:
        return None
    
    r = row[0]
    fn  = decrypt_bytes_to_str(r[1])
    ln  = decrypt_bytes_to_str(r[2])
    em  = decrypt_bytes_to_str(r[3])
    dob = decrypt_bytes_to_str(r[4])
    gt  = decrypt_bytes_to_str(r[5])
    ci  = decrypt_bytes_to_str(r[7])
    return {
        "id": r[0],
        "firstname": fn,
        "lastname": ln,
        "email": em,
        "dateOfBirth": date.fromisoformat(dob) if dob else None,
        "genotype": gt,
        "photo_mime": r[6],
        "city" : ci,
    }

def getRecordsMapRepresentation():
    data = []
    #Only need City, Id, Firstname, LastName
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
        })
    df = pd.DataFrame(data, columns=["id","firstname","lastname","city"])
    return df
    
def giveId(email_real):
    sha = email_sha256(email_real)
    row = _run_query(
        text("SELECT id FROM T_ASPeople WHERE email_sha = :sha LIMIT 1"),
        return_result=True,
        paramsSQL={"sha": sha},
    )
    return int(row[0][0]) if row else None
    
def insertDataFrame():
    df = pd.read_excel("../data/Picture/DataAngelman.xlsx")

    createTable("createASPeople.sql")

    BASE = Path(__file__).resolve().parent / ".." / "data" / "Picture"

    for row in df.itertuples(index=False):
        firstName   = getattr(row, "Firstname")
        lastName    = getattr(row, "Lastname")
        emailAdress = getattr(row, "Email")
        dateOfBirth = getattr(row, "DateOfBirth")
        genotype    = getattr(row, "Genotype")
        fileName    = getattr(row, "File")
        city        = getattr(row, "City")
        
        img_path = BASE / str(fileName)
        photo_data = None
        try:
            if img_path.is_file():
                size = img_path.stat().st_size
                if size <= 4 * 1024 * 1024:
                    with img_path.open("rb") as f:
                        photo_data = f.read()
                else:
                    logger.error("Photo > 4MiB: %s", img_path)
            else:
                logger.warning("Fichier introuvable: %s", img_path)
        except Exception:
            logger.exception("Erreur lecture photo: %s", img_path)

        insertData(firstName, lastName, emailAdress, dateOfBirth, genotype, photo_data, city)

def findId(email):
    id = giveId(email)
    logger.info("Id : %d",id)

def main():
    start = time.time()
    try:
        #insertDataFrame()
        #findId("gustave.faivre@yahoo.fr")
        df = getRecordsMapRepresentation()
        logger.info(df.head())
        elapsed = time.time() - start
        logger.info(f"\n✅ Tables for AS People are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)
    except AppError as e:
        logger.critical("🚨 Error in the AS People process. %s : %s - %s",e.code, e.http_status, str(e))
        sys.exit(1)
    except Exception:
        logger.critical("🚨 Error in the AS People process.")
        sys.exit(1)

if __name__ == "__main__":
     main()
    