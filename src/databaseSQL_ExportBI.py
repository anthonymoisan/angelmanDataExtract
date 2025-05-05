from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
import sshtunnel
import os
from configparser import ConfigParser
import time
import pandas as pd
import numpy as np
import json
import exportBI.exportFASTFrance as expFASTFrance
import smtplib
from email.message import EmailMessage

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


def __tryExecuteRequest(DATABASE_URL, request, returnValue):
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
            if(returnValue):
                data = result.fetchall()
                if data and len(data[0]) == 1:
                    return data[0][0]
                return data
    except Exception as e:
        print("Connexion error :", e)
    finally:
        engine.dispose()
        print("Connexion closed.")


def __execRequest(request,returnValue = False):
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

            if returnValue :
                return __tryExecuteRequest(DATABASE_URL, request, returnValue)
            else:
                __tryExecuteRequest(DATABASE_URL, request,returnValue)
    else:
        # Remote connexion
        DATABASE_URL = f"""mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"""

        if returnValue :
            return __tryExecuteRequest(DATABASE_URL, request, returnValue)
        else:
            __tryExecuteRequest(DATABASE_URL, request,returnValue)


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

def sendEmailAlert(T_TableName, numberOfPreviousRecords, numberOfCurrentRecords):
    msg = EmailMessage()
    msg["Subject"] = "Alert about the Table " + T_TableName
    msg["From"] = "fastfrancecontact@gmail.com"
    msg["To"] = "anthonymoisan@yahoo.fr"
    msg.set_content("Hi,\n\nWe decide to keep the previous database.\n Current Version lines : " +str(numberOfCurrentRecords)+"\n Previous Version Lines : "+str(numberOfPreviousRecords)+"")

    # Paramètres de connexion Gmail
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    username = "fastfrancecontact"
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        password = config['Gmail']['PASSWORD']
        # Send email
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  
                server.login(username, password)
                server.send_message(msg)
                print("Email sent with success !")
        except Exception as e:
            print("Failure to send the email :", e)

def _export_Table(tableName,scriptCreate, reader):
    """
    Method to read a tableName, create the table and read the data
    """
    try:
        start = time.time()
        wkdir = os.path.dirname(__file__)
        
        # 0) Drop Table
        print("--- Drop Table")
        sqlDrop = "DROP TABLE "+ tableName
        __execRequest(sqlDrop)

        # 1) Create Table
        print("--- Create Table")
        with open(f"{wkdir}/SQLScript/"+scriptCreate, "r", encoding="utf-8") as file:
            sql_commands = file.read()
        __execRequest(sql_commands)

        # 2) Use reader to obtain dataframe
        df = reader.readData()
        df = df.replace([np.inf, -np.inf], np.nan)
        df.fillna("None", inplace=True)
        
        # 3) Insert value in Table from dataframe
        __insertValue(df, tableName)
        print("Execute time for "+tableName+ " : ", round(time.time()-start, 2), "s")
    except Exception as e:
        print("an error occures in export_Table "+ tableName+ " : ", e)

def _export_mapFrance(tableName,scriptCreate, reader):
    """
    Method to read map France 
    """
    try:
        start = time.time()
        wkdir = os.path.dirname(__file__)
        # 0) Preprocess
        print("--- Read Data")
        # 1) Use reader to obtain dataframe
        df = reader.readData()
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.astype({col: 'object' for col in df.select_dtypes(include='category').columns})
        df.fillna("None", inplace=True)
        numberofCurrentRecords = df.shape[0]

        # 2) Count the number 
        try:
            sqlCheck = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = " + "'"+ tableName +"'"
            
            result = __execRequest(sqlCheck, returnValue=True)

            if result:
                sqlCount = "SELECT count(*) FROM " + tableName
                numberOfPreviousRecords = __execRequest(sqlCount, returnValue=True)
            else:
                numberOfPreviousRecords = 0
        except Exception as e:
            print("An error occurred while checking or counting table:", e)

        
        if numberofCurrentRecords < 90/100*numberOfPreviousRecords:
            print("--- Preprocess KO")
            print("Failure with the previous data. We keep the previous database") 
            sendEmailAlert(tableName, numberOfPreviousRecords, numberofCurrentRecords )
        else:
            print("--- Preprocess OK")
            # 0) Drop Table
            print("--- Drop Table")
            sqlDrop = "DROP TABLE " + tableName
            __execRequest(sqlDrop)

            # 1) Create Table
            print("--- Create Table")
            with open(f"{wkdir}/SQLScript/" + scriptCreate, "r", encoding="utf-8") as file:
                sql_commands = file.read()
            __execRequest(sql_commands)

            # 2) Insert value in Table from dataframe
            __insertValue(df, tableName)
            print("Execute time for " + tableName +" : ", round(time.time()-start, 2), "s")
    except Exception as e:
        print("an error occures in _export_mapFrance " + tableName+ " : ", e)

def export_RegionsDepartements_French():
    """
    Method to read RegionsDepartements in French
    """
    reader = expFASTFrance.T_RegionsDepartements()
    _export_Table("T_RegionDepartement_French","createRegionDepartement_French.sql", reader)

def export_RegionsPrefectures_French():
    """
    Method to read RegionsPrefectures in French
    """
    reader = expFASTFrance.T_Regions()
    _export_Table("T_RegionPrefecture_French","createPrefectureRegion_French.sql", reader)

def export_DifficultiesSA_French():
    """
    Method to read DifficultiesSA in French
    """
    reader = expFASTFrance.T_DifficultiesSA()
    _export_Table("T_DifficultiesSA_French","createDifficultiesSA_French.sql", reader)

def export_mapFrance_French():
    reader = expFASTFrance.T_MapFASTFrance()
    _export_mapFrance("T_MapFrance_French","createMapFrance_French.sql", reader)

def export_mapFrance_English():
    reader = expFASTFrance.T_MapFASTFrance_EN()
    _export_mapFrance("T_MapFrance_English","createMapFrance_English.sql", reader)

if __name__ == "__main__":
    """
    Endpoint to launch the different scrapers with injection of the results into the database 
    """
    start = time.time()
    export_mapFrance_French()
    print("\n")
    export_mapFrance_English()
    print("\n")
    '''
    export_RegionsDepartements_French()
    print("\n")
    export_RegionsPrefectures_French()
    print("\n")
    export_DifficultiesSA_French()
    
    '''
    print("\nExecute time : ", round(time.time()-start, 2), "s")