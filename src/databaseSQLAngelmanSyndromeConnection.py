import sys, os
from tkinter import Image
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from utilsTools import send_email_alert, _run_query,readTable,_insert_data
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


# Set up logger
logger = setup_logger(debug=False)
wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../angelman_viz_keys/Config4.ini"
config.read(filePath)
key = config['CleChiffrement']['KEY']

cipher = Fernet(key)

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

def insertData(firstname, lastname, emailAddress, dateOfBirth, genotype, photo, city):

    try:
            
        # 1) validations applicatives minimum
        if not isinstance(dateOfBirth, date):
            raise TypeError("dateOfBirth doit être un datetime.date")
        if photo is not None and len(photo) > 4 * 1024 * 1024:
            raise ValueError("Photo > 4 MiB")
        
        detected = detect_mime_from_bytes(photo)      # ex. "image/jpeg"
        photo_mime = normalize_mime(detected or "image/jpeg")

        # 2) chiffrement des champs
        fn_enc   = encrypt_str(firstname)
        ln_enc   = encrypt_str(lastname)
        em_enc   = encrypt_str(emailAddress)  # bytes
        dob_enc  = encrypt_date_like(dateOfBirth)
        gt_enc   = encrypt_str(genotype)
        ci_enc   = encrypt_str(city)

        rowData = {
            "firstname": [fn_enc],
            "lastname": [ln_enc],
            "emailAddress": [em_enc],
            "dateOfBirth": [dob_enc],
            "genotype" : [gt_enc],
            "photo": [photo],
            "photo_mime": [photo_mime], 
            "city": [ci_enc]
        }

        df = pd.DataFrame.from_dict(rowData)
        
        _insert_data(df, "T_ASPeople", if_exists="append")
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

def main():
    start = time.time()
    try:
        
        df = pd.read_excel("../data/Picture/DataAngelman.xlsx")

        createTable("createASPeople.sql")

        for row in df.itertuples(index=False):
            emailAdress = row[3]
            firstName = row[1]
            lastName = row[2]

            dateOfBirth = row[4]
            genotype = row[5]
            city = row[7]
            try:
                img_path = Path("../data/Picture/"+row[6])
                with open(img_path, "rb") as f:
                    photo_data = f.read()
            except:
                logger.error("No file for : %s", img_path)
                raise

            insertData(firstName, lastName, emailAdress, dateOfBirth, genotype, photo_data, city)

        elapsed = time.time() - start
        logger.info(f"\n✅ Tables for AS People are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)
    except Exception:
        logger.critical("🚨 Error in the AS People process.")
        sys.exit(1)

if __name__ == "__main__":
     main()
    