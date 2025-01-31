import scraper.scraperPubMed as scrPubMed
import scraper.scraperASFClinicalTrial as scrASFClinicalTrial
import scraper.scraperASTrial as scrASTrial
import scraper.scraperPopulation as scrPopulation
import time
import os
from configparser import ConfigParser
import json
import pandas as pd


def test_articles_all():
    """
    Articles from PubMed with the scraper
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    df = scrPubMed.pubmed_by_year(1965)
    df.to_csv(f"{wkdir}/../data/pub_details_df.csv") 
    print("---> Execute time for articlesPubMed : ", round(time.time()-start, 2), "s")


def test_ASTrials_all():
    """
    AS trials.csv with the scraper
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    df = scrASTrial.as_trials()
    df.to_csv(f"{wkdir}/../data/all_cities.csv", index=False)
    print("---> Execute time for ASTrials : ", round(time.time()-start, 2), "s")


def test_UnPopulation_all():
    """
    Un Population.csv with the scraper
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../angelman_viz_keys/Config3.ini"
    if config.read(filePath):
        auth_token = config['UnPopulation']['bearerToken']
    df = scrPopulation.un_population(auth_token)
    df.to_csv(f"{wkdir}/../data/un_wpp_pivot_data.csv", index=False)
    print("---> Execute time for UnPopulation : ", round(time.time()-start, 2), "s")


def test_ASFClinicaltrials_all():
    """
    ASF clinical trials.csv with the scraper
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/asf_clinics.json") as f:
        clinics_json = json.load(f)
    clinics_json_df = pd.read_json(f"{wkdir}/../data/asf_clinics.json", orient="index")
    df = scrASFClinicalTrial.trials_asf_clinics(clinics_json_df, clinics_json)
    df.to_csv(f"{wkdir}/../data/asf_clinics_raw_trial_data.csv", index=False)
    print("---> Execute time for ASFClinicalTrials : ", round(time.time()-start, 2), "s") 


if __name__ == "__main__":
    """
    Endpoint to execute the different scrapers in order to have the .csv
    """
    start = time.time()
    print("Tests")
    # Generate csv
    test_ASFClinicaltrials_all()
    test_UnPopulation_all()
    test_articles_all()
    test_ASTrials_all()
    print("Execute Global time : ", round(time.time()-start, 2), "s")
