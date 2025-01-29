# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 18:11:40 2025
API Rest with Flask
@author: antho
"""

# Import de bibliothèques
import flask
from flask import jsonify
import scraper.scraperPubMed as scrPubMed
import scraper.scraperASFClinicalTrial as scrASFClinicalTrial
import scraper.scraperASTrial as scrASTrial
import scraper.scraperPopulation as scrPopulation
from configparser import ConfigParser
import os
import json
import pandas as pd
import math
import time

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    return '''<h1>APIs</h1>
<ul>    
<li>API in order for scraping data from PubMed : <a href="./api/v1/resources/articlesPubMed">./api/v1/resources/articlesPubMed</a></li>
<li>API in order for scraping data from AS Trial : <a href="./api/v1/resources/ASTrials">./api/v1/resources/ASTrials</a></li>
<li>API in order for scraping data from UN Population : <a href="./api/v1/resources/UnPopulation">./api/v1/resources/UnPopulation</a></li>
<li>API in order for scraping data from ASF Clinical Trials : <a href="./api/v1/resources/ASFClinicalTrials">./api/v1/resources/ASFClinicalTrials</a></li>
</ul>
'''


@app.route('/api/v1/resources/articlesPubMed', methods=['GET'])
def api_articles_all():
    start = time.time()
    df =  scrPubMed.pubmed_by_year(1965)
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary
    df.fillna("None",inplace = True)    
    dict_df = df.to_dict(orient='records') 
    print("Execute time for articlesPubMed : ",round(time.time() - start,2), "s")
    return jsonify(dict_df)

@app.route('/api/v1/resources/ASTrials', methods=['GET'])
def api_ASTrials_all():
    start = time.time()
    df =  scrASTrial.as_trials()
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary   
    df.fillna("None",inplace = True)
    dict_df = df.to_dict(orient='records') 
    print("Execute time for ASTrials : ",round(time.time() - start,2), "s")
    return jsonify(dict_df)

@app.route('/api/v1/resources/UnPopulation', methods=['GET'])
def api_UnPopulation_all():
    start = time.time()
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../angelman_viz_keys/Config3.ini"
    if config.read(filePath):
        auth_token = config['UnPopulation']['bearerToken']
    df =  scrPopulation.un_population(auth_token)
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary   
    df.fillna("None",inplace = True)
    dict_df = df.to_dict(orient='records') 
    print("Execute time for UnPopulation : ",round(time.time() - start,2), "s")
    return jsonify(dict_df)

@app.route('/api/v1/resources/ASFClinicalTrials', methods=['GET'])
def api_ASFClinicaltrials_all():
    start = time.time()
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../data/asf_clinics.json") as f:
        clinics_json = json.load(f)
    clinics_json_df = pd.read_json(f"{wkdir}/../data/asf_clinics.json", orient="index")
    df =  scrASFClinicalTrial.trials_asf_clinics(clinics_json_df,clinics_json)
    df.fillna("None",inplace = True)
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary    
    dict_df = df.to_dict(orient='records')
    print("Execute time for ASFClinicalTrials : ",round(time.time() - start,2), "s") 
    return jsonify(dict_df)

 
if __name__ == "__main__":  
    app.run()
