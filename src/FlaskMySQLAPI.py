from flask import Flask, jsonify
from sqlalchemy import create_engine, text
import os
from configparser import ConfigParser

app = Flask(__name__)

wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../angelman_viz_keys/Config2.ini"
config.read(filePath)
DB_HOST = config['MySQL']['DB_HOST']
DB_USERNAME = config['MySQL']['DB_USERNAME']
DB_PASSWORD = config['MySQL']['DB_PASSWORD']
DB_NAME = config['MySQL']['DB_NAME']

DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

@app.route('/recettes', methods=['GET'])
def get_recipes():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM recette"))
            recipes = [dict(row) for row in result.mappings()]
        return jsonify(recipes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)