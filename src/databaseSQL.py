import os
import time
import numpy as np
import pandas as pd

from utilsTools import export_Table
import scraper.scraperPubMed as scrPubMed
import scraper.scraperASTrial as scrASTrial
import scraper.scraperPopulation as scrPopulation
import scraper.scraperClinicalTrial as scrClinicalTrial
from logger import setup_logger

# Logger setup
logger = setup_logger(log_file="steve.log", debug=False)

# === READER CLASSES ===

class PubMedReader:
    def readData(self):
        return scrPubMed.pubmed_by_year(1965)

class ASTrialReader:
    def readData(self):
        return scrASTrial.as_trials()

class UnPopulationReader:
    def readData(self):
        wkdir = os.path.dirname(__file__)
        from configparser import ConfigParser
        config = ConfigParser()
        filePath = f"{wkdir}/../angelman_viz_keys/Config3.ini"
        if config.read(filePath):
            auth_token = config['UnPopulation']['bearerToken']
            return scrPopulation.un_population(auth_token)
        else:
            raise Exception("Config3.ini non trouvé ou invalide")

class ClinicalTrialsReader:
    def readData(self):
        wkdir = os.path.dirname(__file__)
        clinics_json_df = pd.read_json(f"{wkdir}/../data/asf_clinics2.json", orient="index")
        return scrClinicalTrial.trials_clinics_LonLat(clinics_json_df)

# === MAIN FUNCTIONS ===

def articlesPubMed():
    export_Table("T_ArticlesPubMed", "createArticlesPubMed.sql", PubMedReader())

def asTrials():
    export_Table("T_ASTrials", "createASTrials.sql", ASTrialReader())

def unPopulation():
    export_Table("T_UnPopulation", "createUnPopulation.sql", UnPopulationReader())

def clinicalTrials():
    export_Table("T_ClinicalTrials", "createClinicalTrials.sql", ClinicalTrialsReader())

# === LAUNCH ===

if __name__ == "__main__":
    start = time.time()

    articlesPubMed()
    logger.info("\n")
    asTrials()
    logger.info("\n")
    #unPopulation()
    #logger.info("\n")
    #clinicalTrials()
    #logger.info("\n")

    logger.info("Global execution time: %.2fs", time.time() - start)
