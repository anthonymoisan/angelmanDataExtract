from . import utils
from . import error
import pandas as pd
import sys,os
from sqlalchemy import bindparam,text
from datetime import date
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger
from utilsTools import _run_query,_insert_data

# Set up logger
logger = setup_logger(debug=False)

def insertData(firstname, lastname, emailAddress, dateOfBirth, genotype, photo, city):
    try:
            
        # 1) validations applicatives minimum
        if not isinstance(dateOfBirth, date):
            raise TypeError("dateOfBirth doit être un datetime.date")
        dob = utils.coerce_to_date(dateOfBirth)
        if dob > date.today():
            raise error.FutureDateError("dateOfBirth ne peut pas être dans le futur")
        if photo is not None and len(photo) > 4 * 1024 * 1024:
            raise error.PhotoTooLargeError("Photo > 4 MiB")
        
        detected = utils.detect_mime_from_bytes(photo) if photo else None
        photo_mime = utils.normalize_mime(detected or "image/jpeg") if photo else None
        if photo and photo_mime not in {"image/jpeg","image/jpg","image/png","image/webp"}:
            raise error.InvalidMimeTypeError(f"MIME non autorisé: {photo_mime}")

        # 2) chiffrement des champs
        fn_enc   = utils.encrypt_str(firstname)
        ln_enc   = utils.encrypt_str(lastname)
        em_enc   = utils.encrypt_str(emailAddress)  # bytes
        dob_enc  = utils.encrypt_date_like(dateOfBirth)
        gt_enc   = utils.encrypt_str(genotype)
        ci_enc = utils.encrypt_str(city.strip()) if isinstance(city, str) and city.strip() else None

        # hash déterministe pour unicité
        em_sha  = utils.email_sha256(emailAddress)

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
            raise error.DuplicateEmailError("Un enregistrement avec cet email existe déjà") from ie

        lastRowId = _run_query(
        text("SELECT COUNT(*) FROM T_ASPeople"),
        return_result=True)

        return lastRowId[0][0]
    except error.AppError as e:
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
    fn  = utils.decrypt_bytes_to_str(r[1])
    ln  = utils.decrypt_bytes_to_str(r[2])
    em  = utils.decrypt_bytes_to_str(r[3])
    dob = utils.decrypt_bytes_to_str(r[4])
    gt  = utils.decrypt_bytes_to_str(r[5])
    ci  = utils.decrypt_bytes_to_str(r[7])
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
    sha = utils.email_sha256(email_real)
    row = _run_query(
        text("SELECT id FROM T_ASPeople WHERE email_sha = :sha LIMIT 1"),
        return_result=True,
        paramsSQL={"sha": sha},
    )
    return int(row[0][0]) if row else None


    