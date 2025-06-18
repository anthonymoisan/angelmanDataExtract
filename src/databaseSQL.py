import os
import time
import sys
import numpy as np
import pandas as pd

from utilsTools import export_Table
import scraper.scraperPubMed as scrPubMed
import scraper.scraperASTrial as scrASTrial
import scraper.scraperPopulation as scrPopulation
import scraper.scraperClinicalTrial as scrClinicalTrial
from logger import setup_logger

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
        config_path = os.path.join(os.path.dirname(__file__), "../angelman_viz_keys/Config3.ini")
        from configparser import ConfigParser
        config = ConfigParser()
        if config.read(config_path):
            token = config['UnPopulation']['bearerToken']
            return scrPopulation.un_population(token)
        else:
            raise Exception("Config3.ini non trouvé ou invalide")

class ClinicalTrialsReader:
    def readData(self):
        json_path = os.path.join(os.path.dirname(__file__), "../data/asf_clinics2.json")
        df = pd.read_json(json_path, orient="index")
        return scrClinicalTrial.trials_clinics_LonLat(df)


# === EXPORT FUNCTIONS ===

def safe_export(table_name, sql_file, reader, label):
    try:
        logger.info(f"🟡 Export : {label}")
        export_Table(table_name, sql_file, reader)
        logger.info(f"✅ Export OK : {label}\n")
    except Exception as e:
        logger.error(f"❌ Échec KO {label} : {e}")
        raise


# === MAIN ===

def main():
    start = time.time()
    try:
        safe_export("T_ArticlesPubMed", "createArticlesPubMed.sql", PubMedReader(), "Articles PubMed")
        safe_export("T_ASTrials", "createASTrials.sql", ASTrialReader(), "AS Trials")
        # safe_export("T_UnPopulation", "createUnPopulation.sql", UnPopulationReader(), "UN Population")
        # safe_export("T_ClinicalTrials", "createClinicalTrials.sql", ClinicalTrialsReader(), "Clinical Trials")
        elapsed = time.time() - start
        logger.info(f"\n✅ All exports are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)

    except Exception as e:
        logger.critical(f"💥 Error in the export process : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
