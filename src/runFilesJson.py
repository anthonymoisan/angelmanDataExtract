import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from utilsTools import send_email_alert, _run_query,readTable,_insert_data
import time
import logging
from logger import setup_logger
import scraper.scraperHealthData as scrHealthData

# Set up logger
logger = setup_logger(debug=False)

def main():
    start = time.time()
    try:
        elapsed = time.time() - start
        wkdir = os.path.dirname(__file__)
        logger.info(f"🟡 Export : PhamaceuticalOffice.json")
        scrHealthData.pharmaceuticalOffice(f"{wkdir}/../data/")
        logger.info(f"🟡 Export : Ime.json")
        scrHealthData.ime(f"{wkdir}/../data/")
        logger.info(f"\n✅ JSon Files for Angelman Connexion are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)

    except Exception:
        logger.critical("🚨 Error in the Angelman Connexion process.")
        title = "Error in the JSon Files Angelman Connexion"
        message = "Export JSON Files Angelman KO. Check the log"
        #send_email_alert(title, message)
        sys.exit(1)


if __name__ == "__main__":
    main()

