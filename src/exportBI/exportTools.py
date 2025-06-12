from abc import ABC, abstractmethod
import pandas as pd
import requests
import os
from configparser import ConfigParser

class T_ReaderAbstract(ABC):

    def __init__(self):
        self.df = pd.DataFrame()

    @abstractmethod
    def readData(self):
        pass

def get_google_sheet_data(spreadsheet_id,sheet_name, api_key):
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
    
def BuildDataframeFromRegistry(country):
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Registry']['SHEET_ID_REGISTRY']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Data'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['ID2','Sex','Country','FinalDX','Age_2','Month_Join', 'Year_Join']]
        df.rename(columns={"ID2" : "id", "Sex" : "sexe", "Country" : "country", "FinalDX" : "genotype", "Age_2" : "age", "Month_Join" : "monthJoin", "Year_Join" : "yearJoin"},inplace=True)
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df = df[df["country"] == country]
        return df