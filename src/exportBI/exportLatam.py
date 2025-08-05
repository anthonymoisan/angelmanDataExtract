import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import time
from configparser import ConfigParser
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract
    
def _buildDataframeMapLatam():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Latam']['SHEET_ID_MAP_FAST_LATAM']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Hoja 1'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['Fecha de nacimiento', 'Sexo', 'País', 'Ciudad', 'Genotipo' ]]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        return df

def _transformersMapLatam(df):
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

def _transformersMapLatam_EN(df):
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
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right = False
    )  
    return df

def _buildDataframeCapabilities():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Latam']['SHEET_ID_GLOBAL_CAPACITIES']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = "Responses-New"
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].str.strip()

        df.rename(columns={"Population" : "populations", "Condition" : "condition", "Therapy" : "therapy", "Hospital" : "hospital", "Contact PI or Research department" : "contact", "Contact e-mail" : "email", "Contact e-mail 2" : "email2", "Address (City)" : "addressLocation", "Country" : "country", "URL" : "urlWebSite", "Longitude" : "longitude", "Lattitude" : "lattitude"},inplace=True)
        df = df[['populations', 'condition', 'therapy', 'hospital', 'contact', 'email', 'email2', 'addressLocation', 'country', 'urlWebSite', 'longitude', 'lattitude' ]]
        return df

class T_MapLatam(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapLatam()
        self.df = _transformersMapLatam(self.df)
        return self.df

class T_MapLatam_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapLatam()
        self.df = _transformersMapLatam(self.df)
        self.df = _transformersMapLatam_EN(self.df)
        return self.df

class T_Capabilities(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeCapabilities()
        return self.df


if __name__ == "__main__":
  
    reader = T_MapLatam()
    df = reader.readData()
    reader = T_MapLatam_EN()
    df = reader.readData()
    reader = T_Capabilities()
    df = reader.readData()
    print(df.head())
    print(df.shape)
    #print(df.dtypes)

    #resultat = df.groupby('Genotipo').size().reset_index(name='Nombre')
    #print(resultat)
