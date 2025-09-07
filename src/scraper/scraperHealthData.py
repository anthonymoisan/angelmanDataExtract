import os
import sys
import time
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger

# Set up logger
logger = setup_logger( debug=False)

def __requestJSON():
    url = "https://data.opendatasoft.com/api/explore/v2.1/catalog/datasets/healthref-france-finess@public/exports/json"
    params = {
        "select": "rslongue,address,coord,telephone",
        "where": "categetab=620",
    }
    
    response = requests.get(url, params=params)
    return response.json()

def __writeJSON(result,repoPath, nameFileJSon):
    fileJSON = os.path.join(repoPath, nameFileJSon)
    with open(fileJSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

def pharmaceuticalOffice(repoPath):
    resultJSON = __requestJSON()
    __writeJSON(resultJSON,repoPath,"pharmaceuticalOffice.json")


if __name__ == "__main__":
    start = time.time()
    wkdir = os.path.dirname(__file__)
    repoPath = f"{wkdir}/../../data/"
    pharmaceuticalOffice(repoPath)
    logger.info("\nExecute time : %.2fs", time.time() - start)
