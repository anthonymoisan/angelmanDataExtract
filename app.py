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

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    return '''<h1>APIs</h1>
<p>API in order for scraping data from PubMed</p>'''
 
 
@app.route('/api/v1/resources/articlesPubMed/all', methods=['GET'])
def api_all():
    df =  scrPubMed.pubmed_by_year(1965)
    # The fonction jsonify from Flask convert a dictionnary Python
    # in JSON format. We need to convert the dataframe Panda in a dictionnary    
    dict_df = df.to_dict(orient='records') 
    return jsonify(dict_df)
 
  
app.run()
