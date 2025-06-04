import requests
import pandas as pd
import time
import os
from configparser import ConfigParser
from datetime import datetime
from abc import ABC, abstractmethod

def _get_google_sheet_data(spreadsheet_id,sheet_name, api_key):
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
    
def _buildDataframeMapFASTLatam():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Latam']['SHEET_ID_MAP_FAST_LATAM']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Hoja 1'
        sheet_data = _get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['Fecha de nacimiento', 'Sexo', 'País', 'Ciudad', 'Genotipo' ]]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        return df

def _transformersMapFASTLatam(df):
    #Add an index column
    df.index.name = 'index'
    df = df.reset_index()

    #compute Edad
    df['Fecha de nacimiento'] = pd.to_datetime(df['Fecha de nacimiento'], format='%d/%m/%Y', errors='coerce')
    today = pd.to_datetime('today')
    df['Edad'] = df['Fecha de nacimiento'].apply(
        lambda dob: today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )

    #Edad atypic
    df['Edad'] = pd.to_numeric(df['Edad'], errors='coerce')
    df['Edad'] = df['Edad'].fillna(0)
    
    df.drop(columns=["Fecha de nacimiento" ],inplace=True)
    df.rename(columns={"index" : "indexation", "Sexo" : "sexo", "País" : "pais", "Ciudad" : "ciudad", "Genotipo" : "genotipo", "Edad": "edad"},inplace=True)

    return df

def _transformersMapFASTLatam_EN(df):
    df.rename(columns={"sexo" : "gender", "pais" : "country", "ciudad" : "city", "genotipo" : "genotype", "edad": "age"},inplace=True)
    df["genotype"] = df["genotype"].replace("Deleción","Deletion")
    df["genotype"] = df["genotype"].replace("Mutación UBE3A","Mutation")
    df["genotype"] = df["genotype"].replace("Sospecha clinica","Clinical")
    df["genotype"] = df["genotype"].replace("Diagnóstico Clínico","Clinical")
    df["genotype"] = df["genotype"].replace("Lo perdio","I don't know")
    df["genotype"] = df["genotype"].replace("Defecto en centro de impronta ICD","ICD")
    df["genotype"] = df["genotype"].replace("Disomía uniparental UPD","UPD")
    df["gender"] = df["gender"].replace("Hombre","M")
    df["gender"] = df["gender"].replace("Mujer","F")
    df["groupAge"] = pd.cut(
        df["age"],
        bins=[-1, 4, 8, 12, 17, 1000],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right=True
    )  
    return df

class T_ReaderAbstract(ABC):

    def __init__(self):
        self.df = pd.DataFrame()

    @abstractmethod
    def readData(self):
        pass

class T_MapFASTLatam(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapFASTLatam()
        self.df = _transformersMapFASTLatam(self.df)
        return self.df

class T_MapFASTLatam_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapFASTLatam()
        self.df = _transformersMapFASTLatam(self.df)
        self.df = _transformersMapFASTLatam_EN(self.df)
        return self.df
    
if __name__ == "__main__":
  
    reader = T_MapFASTLatam()
    df = reader.readData()
    reader = T_MapFASTLatam_EN()
    df = reader.readData()
    print(df.head())
    print(df.shape)
    #print(df.dtypes)

    #resultat = df.groupby('Genotipo').size().reset_index(name='Nombre')
    #print(resultat)
