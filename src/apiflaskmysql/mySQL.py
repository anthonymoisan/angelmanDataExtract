from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
import sshtunnel
#import MySQLdb
import os
from configparser import ConfigParser

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

sshtunnel.SSH_TIMEOUT = 10.0
sshtunnel.TUNNEL_TIMEOUT = 10.0

# Création du tunnel SSH
with SSHTunnelForwarder(
    (SSH_HOST),
    ssh_username=SSH_USERNAME,
    ssh_password=SSH_PASSWORD,
    remote_bind_address=(DB_HOST, 3306)
) as tunnel:

    # connection = MySQLdb.connect(
    #     user=DB_USERNAME,
    #     passwd=DB_PASSWORD,
    #     host='127.0.0.1', port=tunnel.local_bind_port,
    #     db=DB_NAME
    # )
    # connection.close()

    # # ***/ """
    local_port = tunnel.local_bind_port
    DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@127.0.0.1:{local_port}/{DB_NAME}"
    
    # # Création du moteur SQLAlchemy
    engine = create_engine(DATABASE_URL)

    # Tester la connexion
    try:
        with engine.connect() as connection:
             print("Connect to the database via SSH Tunnel !")

             # Exécuter une requête SQL
             result = connection.execute(text("SELECT * FROM recette"))
             for row in result:
                print(row)
    except Exception as e:
         print("Connexion error :", e)
    finally:
        engine.dispose()
        print("Connexion closed.")
    
