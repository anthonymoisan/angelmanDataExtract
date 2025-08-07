import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from utilsTools import send_email_alert, _run_query,readTable,_insert_data
import time
import logging
from logger import setup_logger
import pandas as pd
from cryptography.fernet import Fernet
from configparser import ConfigParser

# Set up logger
logger = setup_logger(debug=False)
wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../angelman_viz_keys/Config4.ini"
config.read(filePath)
key = config['CleChiffrement']['KEY']

cipher = Fernet(key)

def createTable(sql_script):
    script_path = os.path.join(os.path.dirname(__file__), "angelmanSyndromeConnexion/SQL", sql_script)
    with open(script_path, "r", encoding="utf-8") as file:
        logger.info("--- Create Table.")
        _run_query(file.read())

def encrypt(data):
    return cipher.encrypt(data.encode()).decode()

# Fonction de déchiffrement
def decrypt(encrypted_data):
    try:
        return cipher.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        print("Erreur lors du déchiffrement:", e)
        return None
    
def insertData(emailAdress,firstName,lastName,genotype,gender,age,groupAge,country,region):
    
    
    sql_scriptTablePrincipal = """INSERT INTO T_AngelmanSyndromeConnexion 
                                (gender, genotype, age, groupAge, country, region)
                                VALUES (:gender, :genotype, :age, :groupAge, :country, :region)
                                """


    rowData = {
        "gender": [gender],
        "genotype": [genotype],
        "age": [age],
        "groupAge": [groupAge],
        "country": [country],
        "region": [region]
    }

    df = pd.DataFrame.from_dict(rowData)
    """
    df["groupAge"] = pd.cut(
        pd.Series(df["age"].astype(int)),
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right = False
    )
    """
    _insert_data(df, "T_AngelmanSyndromeConnexion",if_exists='append')
    
    #It works because the index begins to 1
    countSQL = "SELECT count(*) from T_AngelmanSyndromeConnexion"
    last_Records = _run_query(countSQL,return_result=True)
    
    encrypted_data = {
        "id": last_Records,
        "email": [encrypt(emailAdress)],
        "firstname": [encrypt(firstName)],
        "lastname": [encrypt(lastName)]
    }

    df_crypted = pd.DataFrame.from_dict(encrypted_data)
    _insert_data(df_crypted, "T_Crypte",if_exists='append')

def readTableAngelmanSyndromeConnexion():
    sql_tableAngelman = "SELECT * FROM T_AngelmanSyndromeConnexion"
    result = _run_query(sql_tableAngelman,return_result=True)

    rows = []
    for res in result:
        rows.append({
            "id": res[0],
            "gender" : res[1], 
            "genotype" : res[2],
            "age": res[3],
            "groupAge" : res[4],
            "country" : res[5], 
            "region" : res[6]
        })
    
    df_angelman = pd.DataFrame(rows)
    return df_angelman
    
def readTableCrypt():
    sql_tableCrypt = "SELECT * FROM T_Crypte"
    result = _run_query(sql_tableCrypt,return_result=True)

    decrypted_rows = []
    for res in result:
        decrypted_rows.append({
            "id": res[0],
            "firstname": decrypt(res[1]),
            "lastname": decrypt(res[2]),
            "email": decrypt(res[3])
        })
    
    df_decrypted = pd.DataFrame(decrypted_rows)
    return df_decrypted
    
def buildDataFrame():
    df_crypt = readTableCrypt()
    df_angelman = readTableAngelmanSyndromeConnexion()
    df = pd.merge(df_angelman, df_crypt, on='id', how='inner')
    return df

def dropTables():
    sqlCrypte = "DROP TABLE T_Crypte"
    _run_query(sqlCrypte)
    sqlAngelman = "DROP TABLE T_AngelmanSyndromeConnexion"
    _run_query(sqlAngelman)

def main():
    start = time.time()
    try:
        createTable("createAngelmanSydromeConnection.sql")
        createTable("createTableCrypte.sql")
        
        emailAdress = "anthonymoisan@yahoo.fr"
        firstName = "Héloïse"
        lastName = "Moisan"

        genotype = 'Deletion'
        gender = 'Female'
        groupAge = '12-17 years'
        age = 15
        country = 'France'
        region = 'Ile de France'
    
        insertData(emailAdress,firstName,lastName,genotype,gender,age,groupAge,country,region)
        
        emailAdress = "prestat@yahoo.com"
        firstName = "Rodger"
        lastName = "Feder"

        genotype = 'Mutation'
        gender = 'Male'
        groupAge = '>18 years'
        age = 18
        country = 'Algeria'
        region = ''
        insertData(emailAdress,firstName,lastName,genotype,gender,age,groupAge,country,region)
        
        df = buildDataFrame()
        logger.info(df.iloc[0])
        logger.info(df.iloc[1])
        
        dropTables()
        elapsed = time.time() - start
        logger.info(f"\n✅ Tables for Angelman Syndrome Connexion are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)

    except Exception:
        logger.critical("🚨 Error in the Angelman Syndrome Connexion process.")
        title = "Error in the Tables Angelman Syndrome Connexion"
        message = "Export Tables Angelman Syndrome KO. Check the log"
        #send_email_alert(title, message)
        sys.exit(1)

if __name__ == "__main__":
     main()
    