import os
import sys
import time
import requests
import json
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from tools.logger import setup_logger

# Set up logger
logger = setup_logger( debug=False)

def __requestJSON(numCat):
    url = "https://data.opendatasoft.com/api/explore/v2.1/catalog/datasets/healthref-france-finess@public/exports/json"
    params = {
        "select": "rs,rslongue,address,coord,telephone",
        "where": "categetab=" + str(numCat),
    }
    
    response = requests.get(url, params=params)
    return response.json()

def __writeJSON(result,repoPath, nameFileJSon):
    fileJSON = os.path.join(repoPath, nameFileJSon)
    with open(fileJSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

def pharmaceuticalOffice(repoPath):
    resultJSON = __requestJSON(numCat=620)
    __writeJSON(resultJSON,repoPath,"pharmaceuticalOffice.json")

def ime(repoPath):
    resultJSON = __requestJSON(numCat=183)
    __writeJSON(resultJSON,repoPath,"ime.json")

def mas(repoPath):
    resultJSON = __requestJSON(numCat=255)
    __writeJSON(resultJSON,repoPath,"mas.json")
    
def fam(repoPath):
    resultJSON = __requestJSON(numCat=437)
    __writeJSON(resultJSON,repoPath,"fam.json")

def mdph(repoPath):
    resultJSON = __requestJSON(numCat=609)
    __writeJSON(resultJSON,repoPath,"mdph.json")

def camps(repoPath):
    resultJSON = __requestJSON(numCat=190)
    __writeJSON(resultJSON,repoPath,"camps.json")



if __name__ == "__main__":
    start = time.time()
    wkdir = os.path.dirname(__file__)
    repoPath = f"{wkdir}/../../data/"
    pharmaceuticalOffice(repoPath)
    ime(repoPath)
    mas(repoPath)
    fam(repoPath)
    mdph(repoPath)
    camps(repoPath)
    logger.info("\nExecute time : %.2fs", time.time() - start)
