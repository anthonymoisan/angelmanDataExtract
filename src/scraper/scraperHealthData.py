import os
import sys
import time
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger

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

if __name__ == "__main__":
    start = time.time()
    wkdir = os.path.dirname(__file__)
    repoPath = f"{wkdir}/../../data/"
    pharmaceuticalOffice(repoPath)
    ime(repoPath)
    logger.info("\nExecute time : %.2fs", time.time() - start)
