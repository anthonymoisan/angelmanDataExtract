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
    verifySecretAnswer, authenticate_and_get_id, authenticate_email_password, update_person_connection_status
)
from angelmanSyndromeConnexion.peopleRead import( 
    getQuestionSecrete, getRecordsPeople, fetch_person_decrypted, giveId,identity_public, getListPaysTranslate
)
from angelmanSyndromeConnexion.peopleDelete import deleteDataById
from angelmanSyndromeConnexion.peopleCreate import insertData
#from angelmanSyndromeConnexion.geo_utils2 import get_place_maptiler
from angelmanSyndromeConnexion.geo_utils3 import get_place_here

import time
from angelmanSyndromeConnexion import error
from tools.utilsTools import dropTable,createTable

# Set up logger
logger = setup_logger(debug=False)

def _insertDataFrame(firstRow=False):

    dropTable("T_People_Identity",bAngelmanResult=False)
    dropTable("T_People_Public",bAngelmanResult=False)    
    
    wkdir = os.path.dirname(__file__)
    df = pd.read_excel(f"{wkdir}/../../../data/Picture/AS_people_4000_generated.xlsx")
    
    script_path2 = os.path.join(f"{wkdir}/../SQL/","createPublicPeople.sql")
    createTable(script_path2,bAngelmanResult=False)

    script_path = os.path.join(f"{wkdir}/../SQL/","createPeopleIdentity.sql")
    createTable(script_path,bAngelmanResult=False)

    BASE = Path(__file__).resolve().parent / "../../.." / "data" / "Picture"

    if (firstRow):
        loop = 1
    else:
        loop = 10000

    countloop = 0
    countGPSError = 0

    for row in df.itertuples(index=False):
        gender      = getattr(row, "Gender")
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
        is_info = getattr(row, "IsInfo")

        
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

        try:
            insertData(gender, firstName, lastName, emailAdress, dateOfBirth, genotype, photo_data, longitude, latitude, password, questionSecrete, reponseSecrete, is_info)
        except error.BadLocalization as e:
            logger.error(e)
            countGPSError += 1
        countloop += 1

        logger.info("Deal with line %d",countloop)

        if(countloop == loop):
            logger.info("-->GPS error %d",countGPSError)
            break

    

def findId(email):
    id = giveId(email)
    logger.info("Id : %d",id)

#permet de supprimer les individus jusqu'à un idMaximum
def cleanDataBase(idMax):
    for i in range(idMax):
        try:
            ok = deleteDataById(i)
            if ok :
                logger.info(f"ID {i} delete !")
        except Exception as e:
            # Ignore si l'ID n'existe pas
            logger.info(f"ID {i} skipped ({e})")
            continue

def cleanPeople(id):
    try:
        ok = deleteDataById(id)
        if ok :
            logger.info(f"ID {id} delete !")
    except Exception as e:
        # Ignore si l'ID n'existe pas
        logger.info(f"ID {id} skipped ({e})")

def main():
    start = time.time()
    try:
        
        #_insertDataFrame(firstRow=False)
        #findId("anthonymoisan@yahoo.fr")
        #df = getRecordsPeople()
        #logger.info(df.head())
        #dictRes = fetch_person_decrypted(4068)
        #logger.info(dictRes)
        #dictR = identity_public(1)
        #logger.info(dictR)
        #id = authenticate_and_get_id("anthonymoisan@yahoo.fr", "Mmas&37814", bAngelmanResult=False ) 
        #logger.info("Id : %d", id)
        #logger.info("Authentification : %d", authenticate_email_password("anthonymoisan@yahoo.fr", "Mmas&37814", bAngelmanResult=False))
        
        '''
        updateData(
            email_address="victor.cochonneau@gmail.fr", 
            gender='M',
            firstname="Anthony",
            dateOfBirth = "26/11/2019",
            emailNewAddress = "anthonymoisan2@yahoo.fr",
            genotype = "Mutation",             
            password="Mmas|3783",
            longitude = "2.5",
            latitude = "48",
            questionSecrete=2,
            reponseSecrete="Chun Connery",
            is_info=False
        )
        '''

        #update_person_connection_status(person_id= 2, is_connected=False)
        
   
        #deleteDataById(56)
        #logger.info(getQuestionSecrete(8))
        #logger.info(verifySecretAnswer(email="octave.mis@gmail.com",answer="Chrun",bAngelmanResult=False))
        #logger.info(getListPaysTranslate("pl"))
        #logger.info(get_place_maptiler(lat=48.8566, lon=2.3522, api_key="YOUR KEY", language="fr"))
        #logger.info(get_place_here(lat=48.8566, lon=2.3522, api_key="YOUR KEY", language="fr"))
        #cleanDataBase(5)
        #cleanPeople(4067)
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
