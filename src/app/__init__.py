import os
from flask import Flask
from flask_cors import CORS
import warnings
try:
    from cryptography.utils import CryptographyDeprecationWarning
except Exception:
    # fallback si l'emplacement change
    class CryptographyDeprecationWarning(Warning):
        pass

warnings.filterwarnings(
    "ignore",
    category=CryptographyDeprecationWarning,
    module=r"paramiko\..*",
    message=r".*TripleDES has been moved to cryptography\.hazmat\.decrepit\.ciphers\.algorithms\.TripleDES.*",
)


def create_app():
    app = Flask(__name__)
    app.config.update(
        DEBUG=True,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024 + 16 * 1024,  # 4MiB + marge
    )

    # CORS (ouvre les endpoints /api/* ; durcis ensuite au besoin)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Blueprints (ici on ne branche que v1 pour commencer)
    from app.v1.routes import bp as v1
    app.register_blueprint(v1, url_prefix="/api/v1")

    from app.v2.routes import bp as v2
    app.register_blueprint(v2, url_prefix="/api/v2")

    from app.v3.routes import bp as v3
    app.register_blueprint(v3, url_prefix="/api/v3")

    from app.v4.routes import bp as v4
    app.register_blueprint(v4, url_prefix="/api/v4")

    from app.v5.auth import bp as v5_auth
    from app.v5.mail import bp as v5_mail
    from app.v5.people import bp as v5_people

    app.register_blueprint(v5_auth,   url_prefix="/api/v5")
    app.register_blueprint(v5_mail,   url_prefix="/api/v5")
    app.register_blueprint(v5_people, url_prefix="/api/v5")
    #from app.v5.routes import bp as v5
    #app.register_blueprint(v5, url_prefix="/api/v5")

    from app.v6.routes import bp as v6
    app.register_blueprint(v6, url_prefix="/api/v6")

    @app.get("/")
    def home():
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

        API MAP Global
        API in order for reading data from Map Global : <a href="./api/v3/resources/Map_Global">./api/v3/resources/Map_Global</a>
        <br><br>

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

        API Greece
        <ul>
        <li> API in order for reading data from MapGreece_English : <a href="/api/v4/resources/Greece/MapGreece_English">./api/v4/resources/Greece/MapGreece_English</a>
        <li> API in order for reading data from MapGreece_Greek : <a href="/api/v4/resources/Greece/MapGreece_Greek">./api/v4/resources/Greece/MapGreece_Greek</a>
        </ul>
    
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

    return app
