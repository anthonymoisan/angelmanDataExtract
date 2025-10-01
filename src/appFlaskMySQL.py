from flask import Flask, jsonify,request, Response, abort
from sqlalchemy import create_engine
import os
from configparser import ConfigParser
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import pandas as pd
import time
from angelmanSyndromeConnexion.peopleRepresentation import getRecordsPeople,giveId,fetch_photo,fetch_person_decrypted, insertData,authenticate_and_get_id
from angelmanSyndromeConnexion.pointRemarquable import getRecordsPointsRemarquables,insertPointRemarquable
import json
from datetime import datetime
from logger import setup_logger
from flask_cors import CORS
import base64
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import RequestEntityTooLarge
from angelmanSyndromeConnexion.error import (
    AppError, MissingFieldError, DuplicateEmailError, ValidationError
)

# Set up logger
logger = setup_logger(debug=False)

# Very important parameter to execute locally or remotely (production)
# Détection automatique de l'environnement
LOCAL_CONNEXION = not os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower().startswith("pythonanywhere")


appFlaskMySQL = Flask(__name__)
CORS(appFlaskMySQL, resources={r"/api/*": {"origins": "*"}})
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


# Limite d'upload (4 MiB + petite marge)
appFlaskMySQL.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 + 16 * 1024

@appFlaskMySQL.errorhandler(AppError)
def handle_app_error(e: AppError):
    resp = {"status": "error", "code": e.code, "message": str(e)}
    if e.details: resp["details"] = e.details
    return jsonify(resp), e.http_status

@appFlaskMySQL.errorhandler(IntegrityError)
def handle_integrity(e: IntegrityError):
    # MySQL duplicate unique key -> 1062
    if "1062" in str(getattr(e, "orig", e)):
        err = DuplicateEmailError("Un enregistrement avec cet email existe déjà")
        return handle_app_error(err)
    # autre intégrité BDD:
    return jsonify({"status":"error","code":"db_integrity","message":"Violation d'intégrité"}), 409

@appFlaskMySQL.errorhandler(RequestEntityTooLarge)
def handle_too_large(e: RequestEntityTooLarge):
    # si Flask bloque avant ta logique (MAX_CONTENT_LENGTH)
    return jsonify({"status":"error","code":"payload_too_large","message":"Fichier trop volumineux (>4 MiB)"}), 413


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
        logger.error("Connexion error : %s", e)
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
        logger.error("Execute time for "+ tableName +" : ", round(time.time()-start, 2), "s")
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

    API Brazil
    <ul>
    <li> API in order for reading data from MapBrazil_English : <a href="./api/v4/resources/Brazil/MapBrazil_English">./api/v4/resources/Brazil/MapBrazil_English</a>
    <li> API in order for reading data from MapBrazil_Portuguese : <a href="./api/v4/resources/Brazil/MapBrazil_Portuguese">./api/v4/resources/Brazil/MapBrazil_Portuguese</a>
    </ul>

    API India
    <ul>
    <li> API in order for reading data from MapIndia_English : <a href="/api/v4/resources/India/MapIndia_English">./api/v4/resources/India/MapIndia_English</a>
    <li> API in order for reading data from MapIndia_Hindi : <a href="/api/v4/resources/India/MapIndia_Hindi">./api/v4/resources/India/MapIndia_Hindi</a>
    </ul>
    
    API Indonesia
    <ul>
    <li> API in order for reading data from MapIndonesia_English : <a href="/api/v4/resources/Indonesia/MapIndonesia_English">./api/v4/resources/India/MapIndonesia_English</a>
    <li> API in order for reading data from MapIndonesia_Ind : <a href="/api/v4/resources/Indonesia/MapIndonesia_Ind">./api/v4/resources/Indonesia/MapIndonesia_Ind</a>
    </ul>

    API MAP Global
    API in order for reading data from Map Global : <a href="./api/v3/resources/Map_Global">./api/v3/resources/Map_Global</a>
    <br><br>

    API Angelman Syndrome Connexion
    <ul>
    <li>API in order for reading data from the first picture : <a href="./api/v5/people/1/photo">./api/v5/people/1/photo</a></li>
    <li>API in order for reading data from the first info : <a href="./api/v5/people/1/info">./api/v5/people/1/info</a></li>
    <li>API in order for reading a record from emailAddress : <a href="./api/v5/people/lookup?emailAddress=mathys.rob@gmail.com">./api/v5/api/v5/people/lookup?emailAddress=mathys.rob@gmail.com</a></li>
    <li>API in order for reading records for People : <a href="./api/v5/peopleMapRepresentation">./api/v5/peopleMapRepresentation</a></li>
    <li>API in order for reading records for PointRemarquable : <a href="./api/v5/pointRemarquableRepresentation">./api/v5/pointRemarquableRepresentation</a></li>
    </ul>
    
    API Health Data Hub
    <ul>
    <li>API in order for reading data from HDH for pharmaceutical offices : <a href="./api/v6/resources/PharmaceuticalOffice">./api/v6/resources/PharmaceuticalOffice</a></li>
    <li>API in order for reading data from HDH for ime : <a href="./api/v6/resources/Ime">./api/v6/resources/Ime</a></li>
    <li>API in order for reading data from HDH for mas : <a href="./api/v6/resources/Mas">./api/v6/resources/Mas</a></li>
    <li>API in order for reading data from HDH for fam : <a href="./api/v6/resources/Fam">./api/v6/resources/Fam</a></li>
    <li>API in order for reading data from HDH for camps : <a href="./api/v6/resources/Camps">./api/v6/resources/Camps</a></li>
    <li>API in order for reading data from HDH for mdph : <a href="./api/v6/resources/Mdph">./api/v6/resources/Mdph</a></li>
    </ul>
    
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

@appFlaskMySQL.route('/api/v4/resources/Brazil/MapBrazil_English', methods=['GET'])
def api_MapBrazil_English():
    """
    API to expose the results from MapBrazil in English with the specific table from the database
    """
    return __api_Table('T_MapBrazil_English')

@appFlaskMySQL.route('/api/v4/resources/Brazil/MapBrazil_Portuguese', methods=['GET'])
def api_MapBrazil_Portuguese():
    """
    API to expose the results from MapBrazil in Portuguese with the specific table from the database
    """
    return __api_Table('T_MapBrazil_Portuguese')


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

@appFlaskMySQL.route('/api/v4/resources/India/MapIndia_English', methods=['GET'])
def api_MapIndia_English():
    """
    API to expose the results from Map India in English with the specific table from the database
    """
    return __api_Table('T_MapIndia_English')

@appFlaskMySQL.route('/api/v4/resources/India/MapIndia_Hindi', methods=['GET'])
def api_MapIndia_Hindi():
    """
    API to expose the results from Map India in Hindi in English with the specific table from the database
    """
    return __api_Table('T_MapIndia_Hindi')

@appFlaskMySQL.route('/api/v4/resources/Indonesia/MapIndonesia_English', methods=['GET'])
def api_MapIndonesia_English():
    """
    API to expose the results from Map Indonesia in English with the specific table from the database
    """
    return __api_Table('T_MapIndonesia_English')

@appFlaskMySQL.route('/api/v4/resources/Indonesia/MapIndonesia_Ind', methods=['GET'])
def api_MapIndonesia_Ind():
    """
    API to expose the results from Map Indonesia in Ind in English with the specific table from the database
    """
    return __api_Table('T_MapIndonesia_Ind')

def safe_get(data, key, default=""):
    """Retourne la valeur du champ ou une valeur par défaut."""
    return data.get(key) if data.get(key) not in [None, ""] else default


@appFlaskMySQL.route('/api/v5/people/<int:person_id>/photo', methods=['GET'])
def person_photo(person_id):
    photo, mime = fetch_photo(person_id)
    if not photo:
        abort(404)
    return Response(photo, mimetype=mime)

@appFlaskMySQL.route('/api/v5/people/<int:person_id>/info', methods=['GET'])
def person_info(person_id):
    result = fetch_person_decrypted(person_id)
    return jsonify(result)


@appFlaskMySQL.route('/api/v5/auth/login', methods=['POST'])
def auth_login():
    # 1) Essaie JSON
    data = request.get_json(silent=True)

    # 2) Si pas de JSON, tente le form (x-www-form-urlencoded / multipart)
    if not isinstance(data, dict) or not data:
        data = request.form.to_dict(flat=True)

    # 3) Fallback ultime : query string (utile pour tests)
    if not data:
        data = request.args.to_dict(flat=True)

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""


    if not email or not password:
        return jsonify({"error": "email et password sont requis"}), 400

    try:
        person_id = authenticate_and_get_id(email, password)
    except Exception as e:
        # Évite de logger le mot de passe !
        appFlaskMySQL.logger.exception("Erreur d'authentification")
        return jsonify({"error": "erreur serveur"}), 500

    if person_id is None:
        return jsonify({"ok": False, "message": "identifiants invalides"}), 401

    return jsonify({"ok": True, "id": person_id}), 200



@appFlaskMySQL.route('/api/v5/peopleMapRepresentation', methods=['GET'])
def peopleMapRepresentation():
    df = getRecordsPeople()
    return jsonify(df.to_dict(orient="records"))


@appFlaskMySQL.route('/api/v5/pointRemarquableRepresentation', methods=['GET'])
def pointRemarquableRepresentation():
    df = getRecordsPointsRemarquables()
    return jsonify(df.to_dict(orient="records"))

# --- utilitaires ---
def parse_date_any(s: str) -> date:
    """
    Accepte 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM:SS', 'DD/MM/YYYY' ou 'MM/DD/YYYY'.
    Retourne datetime.date.
    """
    s = (s or "").strip()
    # ISO date ou datetime ISO
    try:
        return date.fromisoformat(s.split("T")[0].split(" ")[0])
    except Exception:
        pass
    # DD/MM/YYYY
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        pass
    # MM/DD/YYYY
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except Exception:
        pass
    raise ValueError("dateOfBirth invalide. Formats acceptés: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, DD/MM/YYYY, MM/DD/YYYY")

def _get_src():
    # unifie la source ; multipart => request.form ; sinon JSON
    ctype = (request.content_type or "")
    if ctype.startswith("multipart/form-data"):
        return request.form
    return request.get_json(silent=True) or {}

def get_payloadPeople_from_request():
    """
    Retourne (firstname, lastname, emailAddress, dateOfBirth(date), genotype, photo_bytes, city).
    Supporte multipart/form-data et JSON.
    """
    src = _get_src()

    if request.content_type and request.content_type.startswith("multipart/form-data"):
        form = request.form
        firstname    = form.get("firstname")
        lastname     = form.get("lastname")
        emailAddress = form.get("emailAddress")
        dob_str      = form.get("dateOfBirth")
        genotype     = form.get("genotype")
        long         = form.get("longitude")
        lat          = form.get("latitude")
        password     = form.get("password")
        qSec         = form.get("qSecrete")
        rSec         = form.get("rSecrete")
        file = request.files.get("photo")
        photo_bytes = file.read() if file else None
    else:
        data = request.get_json(silent=True) or {}
        firstname    = data.get("firstname")
        lastname     = data.get("lastname")
        emailAddress = data.get("emailAddress")
        dob_str      = data.get("dateOfBirth")
        genotype     = data.get("genotype")
        long         = data.get("longitude")
        lat          = data.get("latitude")
        password     = data.get("password")
        qSec         = data.get("qSecrete")
        rSec         = data.get("rSecrete")
        # photo en base64 optionnelle
        photo_b64    = data.get("photo_base64")
        if photo_b64:
            # accepte "data:image/jpeg;base64,...." ou juste la base64
            if "," in photo_b64:
                photo_b64 = photo_b64.split(",", 1)[1]
            photo_bytes = base64.b64decode(photo_b64)
        else:
            photo_bytes = None

    # normalisation / conversion
    try:
        # gère "," décimale (FR)
        longC = float(str(long).replace(",", "."))
        latC = float(str(lat).replace(",", "."))
    except ValueError:
        raise ValidationError("longitude/latitude doivent être numériques")

    # bornes WGS84
    if not (-180.0 <= longC <= 180.0):
        raise ValidationError("longitude hors plage [-180, 180]")
    if not (-90.0 <= latC <= 90.0):
        raise ValidationError("latitude hors plage [-90, 90]")
    
    # Champs requis
    required = ["firstname","lastname","emailAddress","dateOfBirth","genotype","longitude", "latitude", "password", "qSecrete", "rSecrete"]
    # Considère vide / espaces comme manquant
    def is_missing(v): return v is None or (isinstance(v, str) and v.strip() == "")
    missing = [k for k in required if is_missing(src.get(k))]

    if missing:
        raise MissingFieldError(
            f"Champs manquants: {', '.join(missing)}",
            details={"missing": missing}
        )
        return {k: src[k] for k in required}

    dob = parse_date_any(dob_str)
    return firstname, lastname, emailAddress, dob, genotype, photo_bytes, longC, latC, password, qSec, rSec


@appFlaskMySQL.route("/api/v5/people", methods=['POST'])
def create_person():
    try:
        fn, ln, email, dob, gt, photo_bytes, long, lat, password, qSec, rSec = get_payloadPeople_from_request()

        new_id = insertData(fn, ln, email, dob, gt, photo_bytes, long, lat, password, qSec, rSec )

        return jsonify({
            "status": "created",
            "id": new_id
        }), 201

    except AppError as e:
        return jsonify({"status": e.http_status, "message": e.code}), e.http_status
    except Exception as e:
        # log détaillé côté serveur
        logger.error("Unhandled error:", e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

def get_payloadPointRemarquable_from_request():
    """
    Retourne (longitude, latitude, short_desc, long_desc).
    Supporte multipart/form-data et JSON.
    """
    src = _get_src()

    # autorise quelques alias
    raw_lon = src.get("longitude") or src.get("lon")
    raw_lat = src.get("latitude")  or src.get("lat")
    short_desc = src.get("short_desc") or src.get("short") or src.get("title")
    long_desc  = src.get("long_desc")  or src.get("description") or ""

    # présence minimale
    missing = []
    def _miss(v): return v is None or (isinstance(v, str) and v.strip() == "")
    if _miss(raw_lon):     missing.append("longitude")
    if _miss(raw_lat):     missing.append("latitude")
    if _miss(short_desc):  missing.append("short_desc")
    if missing:
        raise MissingFieldError(
            f"Champs manquants: {', '.join(missing)}",
            details={"missing": missing}
        )

    # normalisation / conversion
    try:
        # gère "," décimale (FR)
        lon = float(str(raw_lon).replace(",", "."))
        lat = float(str(raw_lat).replace(",", "."))
    except ValueError:
        raise ValidationError("longitude/latitude doivent être numériques")

    # bornes WGS84
    if not (-180.0 <= lon <= 180.0):
        raise ValidationError("longitude hors plage [-180, 180]")
    if not (-90.0 <= lat <= 90.0):
        raise ValidationError("latitude hors plage [-90, 90]")

    sd = str(short_desc).strip()
    ld = str(long_desc).strip()

    return lon, lat, sd, ld



@appFlaskMySQL.route("/api/v5/pointRemarquable", methods=['POST'])
def create_pointRemarquable():
    try:
        longitude, latitude, short_desc, long_desc = get_payloadPointRemarquable_from_request()

        new_id = insertPointRemarquable(longitude, latitude, short_desc, long_desc)

        resp = jsonify({"status": "created", "id": new_id})
        resp.status_code = 201
        resp.headers["Location"] = f"/api/v5/pointRemarquable/{new_id}"
        return resp

    except AppError as e:
        return jsonify({"status": e.http_status, "message": e.code}), e.http_status
    except Exception as e:
        # log détaillé côté serveur
        logger.error("Unhandled error:", e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@appFlaskMySQL.route("/api/v5/people/lookup", methods=['GET'])
def get_idPerson():
    try:
        
        email = request.args.get("email") or request.args.get("emailAddress")
        if not email or not email.strip():
            raise MissingFieldError("email (query param) manquant", {"missing": ["email"]})

        person_id = giveId(email)
        if person_id is None:
            return jsonify({"status": "not_found"}), 404
        else:
            return jsonify({"status": "found", "id": person_id}), 200

    except AppError as e:
        return jsonify({"status": e.http_status, "message": e.code}), e.http_status
    except Exception as e:
        # log détaillé côté serveur
        logger.error("Unhandled error:", e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500



@appFlaskMySQL.route('/api/v6/resources/PharmaceuticalOffice', methods=['GET'])
def api_PharmaceuticalOffice():
    """
    API to expose the results from Pharmaceutical Offices
    """
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/pharmaceuticalOffice.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@appFlaskMySQL.route('/api/v6/resources/Ime', methods=['GET'])
def api_Ime():
    """
    API to expose the results from Ime
    """
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/ime.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@appFlaskMySQL.route('/api/v6/resources/Mas', methods=['GET'])
def api_Mas():
    """
    API to expose the results from Mas
    """
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/mas.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@appFlaskMySQL.route('/api/v6/resources/Fam', methods=['GET'])
def api_fam():
    """
    API to expose the results from Fam
    """
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/fam.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@appFlaskMySQL.route('/api/v6/resources/Mdph', methods=['GET'])
def api_Mdph():
    """
    API to expose the results from Mdph
    """
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/mdph.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@appFlaskMySQL.route('/api/v6/resources/Camps', methods=['GET'])
def api_Camps():
    """
    API to expose the results from Camps
    """
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/camps.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    appFlaskMySQL.run()