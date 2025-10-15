import pandas as pd
import sys,os
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[2]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.logger import setup_logger
from angelmanSyndromeConnexion.peopleUpdate import updateData
from angelmanSyndromeConnexion.peopleAuth import(
    verifySecretAnswer, authenticate_and_get_id, authenticate_email_password
)
from angelmanSyndromeConnexion.peopleRead import( 
    getQuestionSecrete, getRecordsPeople, fetch_person_decrypted, giveId
)
from angelmanSyndromeConnexion.peopleDelete import deleteDataById
from angelmanSyndromeConnexion.peopleCreate import insertData

import time
from angelmanSyndromeConnexion import error
from tools.utilsTools import dropTable,createTable

# Set up logger
logger = setup_logger(debug=False)

def _insertDataFrame(firstRow=False):

    dropTable("T_ASPeople")
    wkdir = os.path.dirname(__file__)
    df = pd.read_excel(f"{wkdir}/../../../data/Picture/DataAngelman.xlsx")
    script_path = os.path.join(f"{wkdir}/../SQL/","createASPeople.sql")
    createTable(script_path)
    BASE = Path(__file__).resolve().parent / "../../.." / "data" / "Picture"

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
        
        #_insertDataFrame(firstRow=False)
        #findId("eva.moreau199@example.org")
        #df = getRecordsPeople()
        #logger.info(df.head())
        #dictRes = fetch_person_decrypted(1)
        #logger.info(dictRes)
        #id = authenticate_and_get_id("victor.cochonneau@gmail.fr", "Mmas&37816" ) 
        #logger.info("Id : %d", id)
        #logger.info("Authentification : %d", authenticate_email_password("gustave.faivre@yahoo.fr", "Mmas&37818"))
        #updateData("anthonymoisan@yahoo.fr", firstname="Robert", password="Mmas|3783",delete_photo=True)
        #deleteDataById(5)
        #logger.info(getQuestionSecrete(7))
        #logger.info(verifySecretAnswer(email="octave.mis@gmail.com",answer="Chun"))

        
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
