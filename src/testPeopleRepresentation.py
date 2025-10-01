from angelmanSyndromeConnexion import utils
import pandas as pd
from pathlib import Path
import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger
from angelmanSyndromeConnexion.peopleRepresentation import insertData, giveId, getRecordsPeople,fetch_person_decrypted, get_email, get_email2
import time
from angelmanSyndromeConnexion import error

# Set up logger
logger = setup_logger(debug=False)

def _insertDataFrame(firstRow=False):

    utils.dropTable("T_ASPeople")
    wkdir = os.path.dirname(__file__)
    df = pd.read_excel(f"{wkdir}/../data/Picture/DataAngelman.xlsx")
    
    utils.createTable("createASPeople.sql")

    BASE = Path(__file__).resolve().parent / ".." / "data" / "Picture"

    if (firstRow):
        loop = 1
    else:
        loop = 1000

    countloop = 0

    for row in df.itertuples(index=False):
        
        firstName   = getattr(row, "Firstname")
        lastName    = getattr(row, "Lastname")
        emailAdress = getattr(row, "Email")
        dateOfBirth = getattr(row, "DateOfBirth")
        genotype    = getattr(row, "Genotype")
        fileName    = getattr(row, "File")
        longitude   = getattr(row, "Longitude")
        latitude    = getattr(row, "Latitude")
        password    = getattr(row, "Password")
        questionSecrete = getattr(row, "QuestionSecrete")
        reponseSecrete = getattr(row, "ReponseSecrete")

        
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

        insertData(firstName, lastName, emailAdress, dateOfBirth, genotype, photo_data, longitude, latitude, password, questionSecrete, reponseSecrete)

        countloop += 1

        logger.info("Deal with line %d",countloop)

        if(countloop == loop):
            break
    

def findId(email):
    id = giveId(email)
    logger.info("Id : %d",id)

def main():
    start = time.time()
    try:
        
        _insertDataFrame(firstRow=False)
        #findId("gustave.faivre@yahoo.fr")
        df = getRecordsPeople()
        #logger.info(df.head())
        #dictRes = fetch_person_decrypted(1)
        #logger.info(dictRes)
        #logger.info("email address : %s", get_email(1))
        #logger.info(get_email2("Heloise","Moisan", "9", "Boulogne-Billancourt"))
        elapsed = time.time() - start
        
        logger.info(f"\n✅ Tables for AS People are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)
    except error.AppError as e:
        logger.critical("🚨 Error in the AS People process. %s : %s - %s",e.code, e.http_status, str(e))
        sys.exit(1)
    except Exception:
        logger.critical("🚨 Error in the AS People process.")
        sys.exit(1)

if __name__ == "__main__":
     main()
