import requests
import pandas as pd
import time
import os
from configparser import ConfigParser

def __get_google_sheet_data(spreadsheet_id,sheet_name, api_key):
    # Construct the URL for the Google Sheets API
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A1:Z?alt=json&key={api_key}'

    try:
        # Make a GET request to retrieve data from the Google Sheets API
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        data = response.json()
        if not data:
            print("Failed to fetch data from Google Sheets API.")

        return data

    except requests.exceptions.RequestException as e:
        # Handle any errors that occur during the request
        print(f"An error occurred: {e}")
        return None
    
def __buildDataframeMapFASTFrance():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['France']['SHEET_ID_MAP_FAST_FRANCE']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Sheet1'
        sheet_data = __get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df.drop(columns=['Subscriber', 'Id', 'Opens','Clicks', 'Sent', 'Subscribed', 'Location', 'Name', 'Last name', 'InteretEssaiClinique', 'Prenom Enfant', 'Nom Enfant' ],inplace=True)
        df.rename(columns={"Année de naissance" : "annee", "Zip" : "code_Departement", "Génotype" : "genotype", "DifficultesSA" : "difficultesSA", "Sexe" : "sexe"},inplace=True)
        return df

def __transformersMapFASTFrance(df):
    df["sexe"] = df["sexe"].replace("Homme", "H")
    df["sexe"] = df["sexe"].replace("Femme", "F")

def __buildDataframeRegionsDepartements(sheet_name):
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['France']['SHEET_ID_REGIONPREFECTURE']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_data = __get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df.rename(columns={"Région" : "region", "Préfecture" : "prefecture"},inplace=True)
        return df
    
def __buildDataframeDifficultiesSA():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['France']['SHEET_ID_DIFFICCULTES']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = "Feuil1"
        sheet_data = __get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df.rename(columns={"DifficultesSA" : "difficultiesSA"},inplace=True)
        return df

def readDataMapFASTFrance():
    df = __buildDataframeMapFASTFrance()
    __transformersMapFASTFrance(df)
    return df

def readDataRegionsDepartements(sheet_name):
    return __buildDataframeRegionsDepartements(sheet_name)
    
def readDataDifficultiesSA():
    return __buildDataframeDifficultiesSA()

if __name__ == "__main__":
    start = time.time()
    df = readDataMapFASTFrance()
    df = readDataRegionsDepartements('RegionDep')
    df = readDataRegionsDepartements('Region')
    df = readDataDifficultiesSA()
    print(df.head())
