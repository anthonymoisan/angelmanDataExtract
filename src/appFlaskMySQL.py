from flask import Flask, jsonify
from sqlalchemy import create_engine, text
import os
from configparser import ConfigParser
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import pandas as pd
import time

#Very important parameter to execute locally or remotely (production)
LOCAL_CONNEXION = True

appFlaskMySQL = Flask(__name__)
appFlaskMySQL.config["DEBUG"] = True

wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../angelman_viz_keys/Config2.ini"
config.read(filePath)
DB_HOST = config['MySQL']['DB_HOST']
DB_USERNAME = config['MySQL']['DB_USERNAME']
DB_PASSWORD = config['MySQL']['DB_PASSWORD']
DB_NAME = config['MySQL']['DB_NAME']

# Need a ssh tunnel in local execution
SSH_HOST = config['SSH']['SSH_HOST']
SSH_USERNAME = config['SSH']['SSH_USERNAME']
SSH_PASSWORD = config['SSH']['SSH_PASSWORD']
sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0

def readTable(DATABASE_URL,tableName):
    try:
        engine = create_engine(DATABASE_URL)        
        with engine.connect() as connection:
            df = pd.read_sql_table(tableName, connection)
            df.fillna("None",inplace = True)    
            dict_df = df.to_dict(orient='records') 
            return jsonify(dict_df)  
    except Exception as e:
         print("Connexion error :", e)
    finally:
        engine.dispose()
      
@appFlaskMySQL.route('/', methods=['GET'])
def home():
    return '''<h1>APIs</h1>
<ul>    
<li>API in order for scraping data from PubMed : <a href="./api/v1/resources/articlesPubMed">./api/v1/resources/articlesPubMed</a></li>
<li>API in order for scraping data from AS Trial : <a href="./api/v1/resources/ASTrials">./api/v1/resources/ASTrials</a></li>
<li>API in order for scraping data from UN Population : <a href="./api/v1/resources/UnPopulation">./api/v1/resources/UnPopulation</a></li>
<li>API in order for scraping data from ASF Clinical Trials : <a href="./api/v1/resources/ASFClinicalTrials">./api/v1/resources/ASFClinicalTrials</a></li>
</ul>
'''

@appFlaskMySQL.route('/api/v1/resources/ASTrials', methods=['GET'])
def api_ASTrials_all():
    start = time.time()
    try:
        if(LOCAL_CONNEXION):
            # Création du tunnel SSH
            with SSHTunnelForwarder(
                (SSH_HOST),
                ssh_username=SSH_USERNAME,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=(DB_HOST, 3306)
            ) as tunnel:
                    local_port = tunnel.local_bind_port
                    DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1:{local_port}/{DB_NAME}"
                    return readTable(DATABASE_URL,"T_ASTrials")
        else:
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
            return readTable(DATABASE_URL,"T_ASTrials")
        print("Execute time for ASTrials : ",round(time.time() - start,2), "s")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@appFlaskMySQL.route('/api/v1/resources/articlesPubMed', methods=['GET'])
def api_articles_all():
    start = time.time()
    try:
        if(LOCAL_CONNEXION):
            # Création du tunnel SSH
            with SSHTunnelForwarder(
                (SSH_HOST),
                ssh_username=SSH_USERNAME,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=(DB_HOST, 3306)
            ) as tunnel:
                    local_port = tunnel.local_bind_port
                    DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1:{local_port}/{DB_NAME}"
                    return readTable(DATABASE_URL,"T_ArticlesPubMed")
        else:
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
            return readTable(DATABASE_URL,"T_ArticlesPubMed")
        print("Execute time for articlesPubMed : ",round(time.time() - start,2), "s")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@appFlaskMySQL.route('/api/v1/resources/UnPopulation', methods=['GET'])
def api_UnPopulation_all():
    start = time.time()
    try:
        if(LOCAL_CONNEXION):
            # Création du tunnel SSH
            with SSHTunnelForwarder(
                (SSH_HOST),
                ssh_username=SSH_USERNAME,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=(DB_HOST, 3306)
            ) as tunnel:
                    local_port = tunnel.local_bind_port
                    DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1:{local_port}/{DB_NAME}"
                    return readTable(DATABASE_URL,"T_UnPopulation")
        else:
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
            return readTable(DATABASE_URL,"T_UnPopulation")
            print("Execute time for UnPopulation : ",round(time.time() - start,2), "s")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@appFlaskMySQL.route('/api/v1/resources/ASFClinicalTrials', methods=['GET'])
def api_ASFClinicaltrials_all():
    start = time.time()
    try:
        if(LOCAL_CONNEXION):
            # Création du tunnel SSH
            with SSHTunnelForwarder(
                (SSH_HOST),
                ssh_username=SSH_USERNAME,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=(DB_HOST, 3306)
            ) as tunnel:
                    local_port = tunnel.local_bind_port
                    DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1:{local_port}/{DB_NAME}"
                    return readTable(DATABASE_URL,"T_ASFClinicalTrials")
        else:
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
            return readTable(DATABASE_URL,"T_ASFClinicalTrials")
        print("Execute time for ASFClinicalTrials : ",round(time.time() - start,2), "s") 
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    appFlaskMySQL.run()