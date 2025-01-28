# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 18:11:40 2025
API Rest with Flask
@author: antho
"""

# Import de bibliothèques
import flask
from flask import jsonify
import scraperPubMed as scrPubMed
import scraperASFClinicalTrial as scrASFClinicalTrial
import scraperASTrial as scrASTrial
import os
import json
import pandas as pd
import math

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    return '''<h1>APIs</h1>
<p>API in order for scraping data from PubMed</p>'''

 
@app.route('/api/v1/resources/articlesPubMed', methods=['GET'])
def api_articles_all():
    df =  scrPubMed.pubmed_by_year(1965)
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary
    df.fillna("None",inplace = True)    
    dict_df = df.to_dict(orient='records') 
    return jsonify(dict_df)

@app.route('/api/v1/resources/ASTrials', methods=['GET'])
def api_ASTrials_all():
    df =  scrASTrial.as_trials()
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary   
    df.fillna("None",inplace = True)
    dict_df = df.to_dict(orient='records') 
    return jsonify(dict_df)

@app.route('/api/v1/resources/ASFClinicalTrials', methods=['GET'])
def api_ASFClinicaltrials_all():
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/asf_clinics.json") as f:
        clinics_json = json.load(f)
    clinics_json_df = pd.read_json(f"{wkdir}/../data/asf_clinics.json", orient="index")
    df =  scrASFClinicalTrial.trials_asf_clinics(clinics_json_df,clinics_json)
    df.fillna("None",inplace = True)
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary    
    dict_df = df.to_dict(orient='records') 
    return jsonify(dict_df)

 
if __name__ == "__main__":  
    app.run()
