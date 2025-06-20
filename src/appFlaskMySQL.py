from flask import Flask, jsonify
from sqlalchemy import create_engine, text
import os
from configparser import ConfigParser
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import pandas as pd
import time

# Very important parameter to execute locally or remotely (production)
LOCAL_CONNEXION = True

appFlaskMySQL = Flask(__name__)
appFlaskMySQL.config["DEBUG"] = True

# Read SSH information and DB information in a file Config2.ini
wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../angelman_viz_keys/Config2.ini"
config.read(filePath)
DB_HOST = config['MySQL']['DB_HOST']
DB_USERNAME = config['MySQL']['DB_USERNAME']
DB_PASSWORD = config['MySQL']['DB_PASSWORD']
DB_NAME = config['MySQL']['DB_NAME']

# Need a ssh tunnel if local execution
SSH_HOST = config['SSH']['SSH_HOST']
SSH_USERNAME = config['SSH']['SSH_USERNAME']
SSH_PASSWORD = config['SSH']['SSH_PASSWORD']
sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0


def __readTable(DATABASE_URL, tableName):
    """
    Read the table from the database

    Arguments:
    DATABASE_URL – URL of the database
    tableName – tableName from database
    """
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            df = pd.read_sql_table(tableName, connection)
            df.fillna("None", inplace=True)
            dict_df = df.to_dict(orient='records')
            return jsonify(dict_df)  
    except Exception as e:
        print("Connexion error :", e)
    finally:
        engine.dispose()

def __api_Table(tableName):
    """
    API to expose the results with the specific table from the database
    """
    start = time.time()
    try:
        if(LOCAL_CONNEXION):
            # Create SSH tunnel
            with SSHTunnelForwarder(
                (SSH_HOST),
                ssh_username=SSH_USERNAME,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=(DB_HOST, 3306)
            ) as tunnel:
                    local_port = tunnel.local_bind_port
                    DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1:{local_port}/{DB_NAME}"
                    return __readTable(DATABASE_URL, tableName)
        else:
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
            return __readTable(DATABASE_URL, tableName)
        print("Execute time for "+ tableName +" : ", round(time.time()-start, 2), "s") 
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@appFlaskMySQL.route('/', methods=['GET'])
def home():
    """
    Explain the endpoints of the API
    """
    return '''<h1>APIs</h1>
    API Steve
    <ul>    
    <li>API in order for scraping data from PubMed : <a href="./api/v1/resources/articlesPubMed">./api/v1/resources/articlesPubMed</a></li>
    <li>API in order for scraping data from AS Trial : <a href="./api/v1/resources/ASTrials">./api/v1/resources/ASTrials</a></li>
    <li>API in order for scraping data from UN Population : <a href="./api/v1/resources/UnPopulation">./api/v1/resources/UnPopulation</a></li>
    <li>API in order for scraping data from Clinical Trials : <a href="./api/v1/resources/ClinicalTrials">./api/v1/resources/ClinicalTrials</a></li>
    </ul>
    
    API Map France
    
    <ul>
    <li>API in order for reading data from MapFrance_French : <a href="./api/v2/resources/FAST_France/MapFrance_French">./api/v2/resources/FAST_France/MapFrance_French</a></li>
    <li>API in order for reading data from DifficultiesSA_French : <a href="./api/v2/resources/FAST_France/DifficultiesSA_French">./api/v2/resources/FAST_France/DifficultiesSA_French</a></li>
    <li>API in order for reading data from RegionDepartement_French : <a href="./api/v2/resources/FAST_France/RegionDepartement_French">./api/v2/resources/FAST_France/RegionDepartement_French</a></li>
    <li>API in order for reading data from RegionPrefecture_French : <a href="./api/v2/resources/FAST_France/RegionPrefecture_French">./api/v2/resources/FAST_France/RegionPrefecture_French</a></li>
    <li>API in order for reading data from DifficultiesSA_English : <a href="./api/v2/resources/FAST_France/DifficultiesSA_English">./api/v2/resources/FAST_France/DifficultiesSA_English</a></li>
    <li>API in order for reading data from MapFrance_English : <a href="./api/v2/resources/FAST_France/MapFrance_English">./api/v2/resources/FAST_France_MapFrance_English</a></li>
    <li>API in order for reading data from Capabilitie : <a href="./api/v2/resources/FAST_France/Capabilities_English">./api/v2/resources/FAST_France_Capabilities_English</a></li>
    </ul>

    API Latam
    <ul>
    <li>API in order for reading data from MapLatam_Spanish : <a href="./api/v2/resources/FAST_Latam/MapLatam_Spanish">./api/v2/resources/FAST_Latam/MapLatam_Spanish</a></li>
    <li>API in order for reading data from MapLatam_English : <a href="./api/v2/resources/FAST_Latam/MapLatam_English">./api/v2/resources/FAST_Latam/MapLatam_English</a></li>
    <li>API in order for reading data from Capabilitie : <a href="./api/v2/resources/FAST_Latam/Capabilities_English">./api/v2/resources/FAST_Latam_Capabilities_English</a></li>
    </ul>

    API Poland
    <ul>
    <li>API in order for reading data from MapLatam_Spanish : <a href="./api/v4/resources/FAST_Poland/MapPoland_Polish">./api/v4/resources/FAST_Poland/MapPoland_Polish</a></li>
    <li>API in order for reading data from MapLatam_English : <a href="./api/v4/resources/FAST_Poland/MapPoland_English">./api/v4/resources/FAST_Poland/MapPoland_English</a></li>
    </ul>

    API Spain
    <ul>
    <li>API in order for reading data from MapSpain_Spanish : <a href="./api/v4/resources/FAST_Spain/MapSpain_Spanish">./api/v4/resources/FAST_Spain/MapSpain_Spanish</a></li>
    <li>API in order for reading data from MapSpain_English : <a href="./api/v4/resources/FAST_Spain/MapSpain_English">./api/v4/resources/FAST_Spain/MapSpain_English</a></li>
    </ul>

    API Australia
    API in order for reading data from Map Australia : <a href="./api/v4/resources/Australia/MapAustralia_English">./api/v4/resources/Australia/MapAustralia_English</a>
    <br><br>

    API USA
    API in order for reading data from Map USA : <a href="./api/v4/resources/USA/MapUSA_English">./api/v4/resources/USA/MapUSA_English</a>
    <br><br>

    API Canada
    API in order for reading data from Map Canada : <a href="./api/v4/resources/Canada/MapCanada_English">./api/v4/resources/Canada/MapCanada_English</a>
    <br><br>

    API UK
    API in order for reading data from Map UK : <a href="./api/v4/resources/UK/MapUK_English">./api/v4/resources/UK/MapUK_English</a>
    <br><br>

    API Italy
    <ul>
    <li> API in order for reading data from MapItaly_English : <a href="./api/v4/resources/Italy/MapItaly_English">./api/v4/resources/Italy/MapItaly_English</a>
    <li> API in order for reading data from MapItaly_Italian : <a href="./api/v4/resources/Italy/MapItaly_Italian">./api/v4/resources/Italy/MapItaly_Italian</a>
    </ul>

    API Germany
    <ul>
    <li> API in order for reading data from MapGermany_English : <a href="./api/v4/resources/Germany/MapGermany_English">./api/v4/resources/Germany/MapGermany_English</a>
    <li> API in order for reading data from MapGermany_Deutsch : <a href="./api/v4/resources/Germany/MapGermany_Deutsch">./api/v4/resources/Germany/MapGermany_Deutsch</a>
    </ul>

    API MAP Global
    API in order for reading data from Map Global : <a href="./api/v3/resources/Map_Global">./api/v3/resources/Map_Global</a>
    '''


@appFlaskMySQL.route('/api/v1/resources/ASTrials', methods=['GET'])
def api_ASTrials_all():
    """
    API to expose the results from AS trials with the specific table from the database
    """
    return __api_Table("T_ASTrials")

@appFlaskMySQL.route('/api/v1/resources/articlesPubMed', methods=['GET'])
def api_articles_all():
    """
    API to expose the results from Pub Med articles with the specific table from the database
    """
    return __api_Table("T_ArticlesPubMed")
    
@appFlaskMySQL.route('/api/v1/resources/UnPopulation', methods=['GET'])
def api_UnPopulation_all():
    """
    API to expose the results from Un Population with the specific table from the database
    """
    return __api_Table("T_UnPopulation")
    
@appFlaskMySQL.route('/api/v1/resources/ClinicalTrials', methods=['GET'])
def api_Clinicaltrials_all():
    """
    API to expose the results from clinical trials with the specific table from the database
    """
    return __api_Table("T_ClinicalTrials")
    
@appFlaskMySQL.route('/api/v2/resources/FAST_France/MapFrance_French', methods=['GET'])
def api_MapFrance_French():
    """
    API to expose the results from MapFrance in French with the specific table from the database
    """
    return __api_Table("T_MapFrance_French")

@appFlaskMySQL.route('/api/v2/resources/FAST_France/DifficultiesSA_French', methods=['GET'])
def api_DifficultiesSA_French():
    """
    API to expose the results from Difficulties SA in French with the specific table from the database
    """
    return __api_Table('T_MapFrance_DifficultiesSA_French')

@appFlaskMySQL.route('/api/v2/resources/FAST_France/RegionDepartement_French', methods=['GET'])
def api_RegionDepartement_French():
    """
    API to expose the results from Region Departement in French with the specific table from the database
    """
    return __api_Table('T_MapFrance_RegionDepartement_French')

@appFlaskMySQL.route('/api/v2/resources/FAST_France/RegionPrefecture_French', methods=['GET'])
def api_RegionPrefecture_French():
    """
    API to expose the results from Region Prefecture in French with the specific table from the database
    """
    return __api_Table('T_MapFrance_RegionPrefecture_French')

@appFlaskMySQL.route('/api/v2/resources/FAST_France/MapFrance_English', methods=['GET'])
def api_MapFrance_English():
    """
    API to expose the results from MapFrance in English with the specific table from the database
    """
    return __api_Table('T_MapFrance_English')

@appFlaskMySQL.route('/api/v2/resources/FAST_France/DifficultiesSA_English', methods=['GET'])
def api_DifficultiesSA_English():
    """
    API to expose the results from DifficultiesSA in English with the specific table from the database
    """
    return __api_Table('T_MapFrance_DifficultiesSA_English')

@appFlaskMySQL.route('/api/v2/resources/FAST_France/Capabilities_English', methods=['GET'])
def api_Capabilities_English():
    """
    API to expose the results from Capabilities in English with the specific table from the database
    """
    return __api_Table('T_MapFrance_Capabilitie')

@appFlaskMySQL.route('/api/v2/resources/FAST_Latam/MapLatam_Spanish', methods=['GET'])
def api_MapLatam_Spanish():
    """
    API to expose the results from MapLatam in Spanish with the specific table from the database
    """
    return __api_Table('T_MapLatam_Spanish')

@appFlaskMySQL.route('/api/v2/resources/FAST_Latam/MapLatam_English', methods=['GET'])
def api_MapLatam_English():
    """
    API to expose the results from MapLatam in English with the specific table from the database
    """
    return __api_Table('T_MapLatam_English')

@appFlaskMySQL.route('/api/v2/resources/FAST_Latam/Capabilities_English', methods=['GET'])
def api_Capabilities_Latam_English():
    """
    API to expose the results from Capabilities in English with the specific table from the database
    """
    return __api_Table('T_MapLatam_Capabilitie')

@appFlaskMySQL.route('/api/v3/resources/Map_Global', methods=['GET'])
def api_MapGlobal():
    """
    API to expose the results from Map Global in English with the specific table from the database
    """
    return __api_Table('T_MapGlobal')

@appFlaskMySQL.route('/api/v4/resources/FAST_Poland/MapPoland_Polish', methods=['GET'])
def api_MapPoland_Polish():
    """
    API to expose the results from MapPoland in Polish with the specific table from the database
    """
    return __api_Table('T_MapPoland_Polish')

@appFlaskMySQL.route('/api/v4/resources/FAST_Poland/MapPoland_English', methods=['GET'])
def api_MapPoland_English():
    """
    API to expose the results from MapPoland in English with the specific table from the database
    """
    return __api_Table('T_MapPoland_English')


@appFlaskMySQL.route('/api/v4/resources/FAST_Spain/MapSpain_Spanish', methods=['GET'])
def api_MapSpain_Spanish():
    """
    API to expose the results from MapSpain in Spanish with the specific table from the database
    """
    return __api_Table('T_MapSpain_Spanish')

@appFlaskMySQL.route('/api/v4/resources/Italy/MapItaly_English', methods=['GET'])
def api_MapItaly_English():
    """
    API to expose the results from MapItaly in English with the specific table from the database
    """
    return __api_Table('T_MapItaly_English')

@appFlaskMySQL.route('/api/v4/resources/Italy/MapItaly_Italian', methods=['GET'])
def api_MapItaly_Italian():
    """
    API to expose the results from MapItaly in Italian with the specific table from the database
    """
    return __api_Table('T_MapItaly_Italian')

@appFlaskMySQL.route('/api/v4/resources/Germany/MapGermany_English', methods=['GET'])
def api_MapGermany_English():
    """
    API to expose the results from MapGermany in English with the specific table from the database
    """
    return __api_Table('T_MapGermany_English')

@appFlaskMySQL.route('/api/v4/resources/Germany/MapGermany_Deutsch', methods=['GET'])
def api_MapGermany_Deutsch():
    """
    API to expose the results from MapGermany in Deutsch with the specific table from the database
    """
    return __api_Table('T_MapGermany_Deutsch')


@appFlaskMySQL.route('/api/v4/resources/FAST_Spain/MapSpain_English', methods=['GET'])
def api_MapSpain_English():
    """
    API to expose the results from MapSpain in English with the specific table from the database
    """
    return __api_Table('T_MapSpain_English')

@appFlaskMySQL.route('/api/v4/resources/Australia/MapAustralia_English', methods=['GET'])
def api_MapAustralia_English():
    """
    API to expose the results from MapAustralia in English with the specific table from the database
    """
    return __api_Table('T_MapAustralia_English')

@appFlaskMySQL.route('/api/v4/resources/USA/MapUSA_English', methods=['GET'])
def api_MapUSA_English():
    """
    API to expose the results from MapUSA in English with the specific table from the database
    """
    return __api_Table('T_MapUSA_English')

@appFlaskMySQL.route('/api/v4/resources/Canada/MapCanada_English', methods=['GET'])
def api_MapCanada_English():
    """
    API to expose the results from MapCanada in English with the specific table from the database
    """
    return __api_Table('T_MapCanada_English')

@appFlaskMySQL.route('/api/v4/resources/UK/MapUK_English', methods=['GET'])
def api_MapUK_English():
    """
    API to expose the results from MapUK in English with the specific table from the database
    """
    return __api_Table('T_MapUK_English')


if __name__ == '__main__':
    appFlaskMySQL.run()