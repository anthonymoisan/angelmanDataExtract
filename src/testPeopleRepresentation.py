from angelmanSyndromeConnexion import utils
import pandas as pd
from pathlib import Path
import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger
from angelmanSyndromeConnexion.peopleRepresentation import insertData, giveId, getRecordsPeople
import time
from angelmanSyndromeConnexion import error

# Set up logger
logger = setup_logger(debug=False)

def _insertDataFrame():

    utils.dropTable("T_ASPeople")
    
    df = pd.read_excel("./../data/Picture/DataAngelman.xlsx")
    
    utils.createTable("createASPeople.sql")

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
        
        _insertDataFrame()
        findId("gustave.faivre@yahoo.fr")
        df = getRecordsPeople()
        logger.info(df.head())
        
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
