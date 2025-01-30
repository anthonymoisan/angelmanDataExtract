from flask import Flask, jsonify
from sqlalchemy import create_engine, text
import os
from configparser import ConfigParser
import sshtunnel
from sshtunnel import SSHTunnelForwarder


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

LOCAL_CONNEXION = True 

def selectSQL(DATABASE_URL,request):
    try:
        engine = create_engine(DATABASE_URL)        
        with engine.connect() as connection:
            result = connection.execute(text(request))
            recipes = [dict(row) for row in result.mappings()]
            return jsonify(recipes)  
    except Exception as e:
         print("Connexion error :", e)
    finally:
        engine.dispose()
      


@appFlaskMySQL.route('/recettes', methods=['GET'])
def get_recipes():
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
                    return selectSQL(DATABASE_URL,"SELECT * FROM recette")
        else:
            DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
            return selectSQL(DATABASE_URL,"SELECT * FROM recette")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    appFlaskMySQL.run()