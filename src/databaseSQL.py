from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
import sshtunnel
import os
from configparser import ConfigParser
import time
import scraper.scraperPubMed as scrPubMed
import scraper.scraperASTrial as scrASTrial
import scraper.scraperPopulation as scrPopulation
import scraper.scraperASFClinicalTrial as scrASFClinicalTrial
import pandas as pd
import numpy as np
import json

# Very important parameter to execute locally or remotely (production)
LOCAL_CONNEXION = True

# Read SSH information and DB information in a file Config2.ini
wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../angelman_viz_keys/Config2.ini"
if config.read(filePath):
    SSH_HOST = config['SSH']['SSH_HOST']
    SSH_USERNAME = config['SSH']['SSH_USERNAME']
    SSH_PASSWORD = config['SSH']['SSH_PASSWORD']
    DB_HOST = config['MySQL']['DB_HOST']
    DB_USERNAME = config['MySQL']['DB_USERNAME']
    DB_PASSWORD = config['MySQL']['DB_PASSWORD']
    DB_NAME = config['MySQL']['DB_NAME']
else:
    print("Config file Ini not found")

# SSH Parameters
sshtunnel.SSH_TIMEOUT = 100.0
sshtunnel.TUNNEL_TIMEOUT = 100.0


def __tryExecuteRequest(DATABASE_URL, request):
    """
    Try execute a request SQL with the SQL request

    Arguments:
    DATABASE_URL : url of the database
    request – SQL request
    """
    # Create engine SQLAlchemy
    engine = create_engine(DATABASE_URL)

    # Try the connexion
    try:
        with engine.connect() as connection:
            print("Connect to the database !")

            # Execute the request SQL
            result = connection.execute(text(request))
    except Exception as e:
        print("Connexion error :", e)
    finally:
        engine.dispose()
        print("Connexion closed.")


def __execRequest(request):
    """
    Execute a request SQL with the parameter request in local or remotely 

    Arguments:
    request – SQL request
    """
    
    if LOCAL_CONNEXION:
        # Create SSH Tunnel
        with SSHTunnelForwarder(
            (SSH_HOST),
            ssh_username=SSH_USERNAME,
            ssh_password=SSH_PASSWORD,
            remote_bind_address=(DB_HOST, 3306)
        ) as tunnel:

            # Local connexion
            local_port = tunnel.local_bind_port
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1: {local_port}/{DB_NAME}"

            __tryExecuteRequest(DATABASE_URL, request)
    else:
        # Remote connexion
        DATABASE_URL = f"""mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"""

        __tryExecuteRequest(DATABASE_URL, request)


def __tryInsertValue(DATABASE_URL, tableName, df):
    """
    Try insert Value from df in tableName with Database_URL 

    Arguments:
    DATABASE_URL – URL of the database
    df – dataframe
    tableName – tableName from database
    """
    # Create engine SQLAlchemy
    engine = create_engine(DATABASE_URL)

    # Try connexion
    try:
        with engine.connect() as connection:
            df.to_sql(tableName, con=connection, if_exists='replace', index=False)
            print("Insert values in ", tableName)
    except Exception as e:
        print("Connexion error :", e)
    finally:
        engine.dispose()
        print("Connexion closed.")


def __insertValue(df, tableName):
    """
    Insert Value from df in tableName 

    Arguments:
    df – dataframe
    tableName – tableName from database
    """
    if LOCAL_CONNEXION:
        # Création du tunnel SSH
        with SSHTunnelForwarder(
            (SSH_HOST),
            ssh_username=SSH_USERNAME,
            ssh_password=SSH_PASSWORD,
            remote_bind_address=(DB_HOST, 3306)
        ) as tunnel:

            # # ***/ """
            local_port = tunnel.local_bind_port
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1:{local_port}/{DB_NAME}"

            __tryInsertValue(DATABASE_URL, tableName, df)
    else:
        # Remotely
        DATABASE_URL = f"""mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"""

        __tryInsertValue(DATABASE_URL, tableName, df)


def asTrials():
    """
    Method to scrap data from as clinical trials
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    # 0) Drop Table
    print("--- Drop Table")
    sqlDrop = "DROP TABLE T_ASTrials"
    __execRequest(sqlDrop)

    # 1) Create Table
    print("--- Create Table")
    with open(f"{wkdir}/SQLScript/createASTrials.sql", "r", encoding="utf-8") as file:
        sql_commands = file.read()
    __execRequest(sql_commands)

    print("--- Scraper")
    # 2) Use scraper to obtain dataframe
    df = scrASTrial.as_trials()
    df = df.replace([np.inf, -np.inf], np.nan)
    df.fillna("None", inplace=True)

    # 3) Insert value in Table from dataframe
    __insertValue(df, "T_ASTrials")
    print("Execute time for ASTrials : ", round(time.time()-start, 2), "s")


def articlesPubMed():
    """
    Method to scrap data from as Pub Med
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    # 0) Drop Table
    print("--- Drop Table")
    sqlDrop = "DROP TABLE T_ArticlesPubMed"
    __execRequest(sqlDrop)

    # 1) Create Table
    print("--- Create Table")
    with open(f"{wkdir}/SQLScript/createArticlesPubMed.sql", "r", encoding="utf-8") as file:
        sql_commands = file.read()
    __execRequest(sql_commands)

    print("--- Scraper")
    # 2) Use scraper to obtain dataframe
    df = scrPubMed.pubmed_by_year(1965)
    df = df.replace([np.inf, -np.inf], np.nan)
    df.fillna("None", inplace=True)

    # 3) Insert value in Table from dataframe
    __insertValue(df, "T_ArticlesPubMed")
    print("Execute time for articlesPubMed : ", round(time.time()-start, 2), "s")


def unPopulation():
    """
    Method to scrap data from Un Population
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    # 0) Drop Table
    print("--- Drop Table")
    sqlDrop = "DROP TABLE T_UnPopulation"
    __execRequest(sqlDrop)

    # 1) Create Table
    print("--- Create Table")
    with open(f"{wkdir}/SQLScript/createUnPopulation.sql", "r", encoding="utf-8") as file:
        sql_commands = file.read()
    __execRequest(sql_commands)

    print("--- Scraper")
    # 2) Use scraper to obtain dataframe
    config = ConfigParser()
    filePath = f"{wkdir}/../angelman_viz_keys/Config3.ini"
    if config.read(filePath):
        auth_token = config['UnPopulation']['bearerToken']
    df = scrPopulation.un_population(auth_token)
    df = df.replace([np.inf, -np.inf], np.nan)
    df.fillna("None", inplace=True)

    # 3) Insert value in Table from dataframe
    __insertValue(df, "T_UnPopulation")
    print("Execute time for UnPopulation : ", round(time.time()-start, 2), "s")


def asfClinicalTrials():
    """
    Method to scrap data from as clinical trials and ASF files
    """
    start = time.time()
    wkdir = os.path.dirname(__file__)
    # 0) Drop Table
    print("--- Drop Table")
    sqlDrop = "DROP TABLE T_ASFClinicalTrials"
    __execRequest(sqlDrop)

    # 1) Create Table
    print("--- Create Table")
    with open(f"{wkdir}/SQLScript/createASFClinicalTrials.sql", "r", encoding="utf-8") as file:
        sql_commands = file.read()
    __execRequest(sql_commands)
    print("--- Scraper")
    # 2) Use scraper to obtain dataframe
    with open(f"{wkdir}/../data/asf_clinics.json") as f:
        clinics_json = json.load(f)
    clinics_json_df = pd.read_json(f"{wkdir}/../data/asf_clinics.json", orient="index")
    df = scrASFClinicalTrial.trials_asf_clinics(clinics_json_df, clinics_json)
    df = df.replace([np.inf, -np.inf], np.nan)
    df.fillna("None", inplace=True)

    # 3) Insert value in Table from dataframe
    __insertValue(df, "T_ASFClinicalTrials")
    print("Execute time for ASFClinicalTrials : ", round(time.time()-start, 2), "s")


if __name__ == "__main__":
    """
    Endpoint to launch the different scrapers with injection of the results into the database 
    """
    start = time.time()
    articlesPubMed()
    print("\n")
    asTrials()
    print("\n")
    unPopulation()
    print("\n")
    asfClinicalTrials()
    print("\nExecute time : ", round(time.time()-start, 2), "s")