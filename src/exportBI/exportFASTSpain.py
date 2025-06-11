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
    
def _buildDataframeMapFASTSpain_EN():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Registry']['SHEET_ID_REGISTRY']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Data'
        sheet_data = _get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['ID2','Sex','Country','FinalDX','Age_2','Month_Join', 'Year_Join']]
        df.rename(columns={"ID2" : "id", "Sex" : "sexe", "Country" : "country", "FinalDX" : "genotype", "Age_2" : "age", "Month_Join" : "monthJoin", "Year_Join" : "yearJoin"},inplace=True)
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df = df[df["country"] == "Spain"]
        #df = df[df["genotype"].isin(["Deletion", "Clinical", "Mutation", "Imprinting centre defect", "Uniparental disomy"])] 
        return df

def _transformersMapFASTSpain_EN(df):
    df["sexe"] = df["sexe"].replace("Male", "M")
    df["sexe"] = df["sexe"].replace("Female", "F")
    df = df.rename(columns={"sexe": "gender"})    

    df["genotype"] = df["genotype"].replace("Uniparental disomy","UPD")
    df["genotype"] = df["genotype"].replace("NA","I don't know")
    df["genotype"] = df["genotype"].replace("Unknown","I don't know")
    df["genotype"] = df["genotype"].replace("Other","I don't know")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","ICD")

    df["age"] = pd.to_numeric(df["age"], errors="coerce")

    df["groupAge"] = pd.cut(
        df["age"],
        bins=[0, 4, 8, 12, 17, 1000],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right=True
    )  

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df

def _transformersMapFASTSpain(df):
    
    df["sexe"] = df["sexe"].replace("Male", "Hombre")
    df["sexe"] = df["sexe"].replace("Female", "Mujer")
    
    df["genotype"] = df["genotype"].replace("Uniparental disomy","Disomía uniparental UPD")
    df["genotype"] = df["genotype"].replace("Clinical","Clinical")
    df["genotype"] = df["genotype"].replace("NA","Lo perdio")
    df["genotype"] = df["genotype"].replace("Unknown","Lo perdio")
    df["genotype"] = df["genotype"].replace("Other","Lo perdio")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","Defecto en centro de impronta ICD")
    df["genotype"] = df["genotype"].replace("Deletion","Deleción")
    df["genotype"] = df["genotype"].replace("Mutation","Mutación")

    df.rename(columns={ "sexe" : "sexo", "genotype" : "genotipo", "age": "edad"},inplace=True)

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df


class T_ReaderAbstract(ABC):

    def __init__(self):
        self.df = pd.DataFrame()

    @abstractmethod
    def readData(self):
        pass

class T_MapFASTSpain_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapFASTSpain_EN()
        self.df = _transformersMapFASTSpain_EN(self.df)
        return self.df

class T_MapFASTSpain(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapFASTSpain_EN()
        self.df = _transformersMapFASTSpain(self.df)
        return self.df
    
if __name__ == "__main__":
  
    reader = T_MapFASTSpain_EN()
    df = reader.readData()
    reader = T_MapFASTSpain()
    df = reader.readData()
    print(df.head())
    print(df.shape)