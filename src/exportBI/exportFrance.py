import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import time
from configparser import ConfigParser
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract

def _buildDataframeMapFrance():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['France']['SHEET_ID_MAP_FAST_FRANCE']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Sheet1'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['Id', 'Année de naissance', 'Zip', 'Génotype', 'DifficultesSA', 'Sexe' ]]
        df.rename(columns={"Id" : "id", "Année de naissance" : "annee", "Zip" : "code_Departement", "Génotype" : "genotype", "DifficultesSA" : "difficultesSA", "Sexe" : "sexe"},inplace=True)
        return df

def _transformersMapFrance(df):
    df["sexe"] = df["sexe"].replace("Homme", "H")
    df["sexe"] = df["sexe"].replace("Femme", "F")
    return df

def _buildDataframeRegionsDepartements(sheet_name):
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['France']['SHEET_ID_REGIONPREFECTURE']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df.rename(columns={"Région" : "region", "Préfecture" : "prefecture"},inplace=True)
        return df
    
def _buildDataframeDifficultiesSA():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['France']['SHEET_ID_DIFFICCULTES']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = "Feuil1"
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df.rename(columns={"DifficultesSA" : "difficultiesSA"},inplace=True)
        return df
    
def _buildDataframeCapabilities():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['France']['SHEET_ID_GLOBAL_CAPACITIES']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = "Capabilies"
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df.rename(columns={"Population" : "populations", "Therapy" : "therapy", "Phase" : "phase", "Capability to realize the phase" : "CapabilityBool", "Hospital" : "hospital", "Contact" : "contact", "Address" : "addressLocation", "Longitude" : "longitude", "Lattitude" : "lattitude", "URL" : "urlWebSite"},inplace=True)
        return df

def _transformersCapabilities(df):
    df["populations"] = df["populations"].replace("- kids < 18 ans","- Kids < 18 ans")
    df = df[df["CapabilityBool"] == "Oui"]
    df = df.drop(columns='CapabilityBool')
    return df

def _transformersDifficultiesSA_EN(df):
    df["difficultiesSA"] = df["difficultiesSA"].replace("Motricité fine","Fine motor")
    df["difficultiesSA"] = df["difficultiesSA"].replace("Motricité globale","Gross motor")
    df["difficultiesSA"] = df["difficultiesSA"].replace("Sommeil","Sleep")
    df["difficultiesSA"] = df["difficultiesSA"].replace("Epilepsie","Seizure")
    df["difficultiesSA"] = df["difficultiesSA"].replace("Comportement","Behavior")
    df["difficultiesSA"] = df["difficultiesSA"].replace("Aucune","None")
    return df

def _transformersMapFrance_EN(df):   
    df["sexe"] = df["sexe"].replace("Homme", "M")
    df["sexe"] = df["sexe"].replace("Femme", "F")
    df["genotype"] = df["genotype"].replace("Délétion","Deletion")
    df["genotype"] = df["genotype"].replace("Disomie uniparentale","UPD")
    df["genotype"] = df["genotype"].replace("Ne sait pas","I don't know")
    df["genotype"] = df["genotype"].replace("Défaut d'empreinte","ICD")
    df["genotype"] = df["genotype"].replace("Forme mosaïque","Mosaic")
    year_current = datetime.now().year
    df["age"] = year_current - pd.to_numeric(df["annee"])
    # Serie groupAge
    df["groupAge"] = pd.cut(
        df["age"],
        bins=[-0.1, 4, 8, 12, 17, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right=True
    )  
    df = df[~df["code_Departement"].isin(["971", "972", "973", "974", "975", "976", "Maroc", "Algerie", "Belgique", "Canada", "Suisse", "Tunisie"])]

    return df

def _transformDifficultiesSA(texte):
    # Dictionnaire de remplacements
    remplacements = {
        "Motricité fine" :"Fine motor",
        "Motricité globale" : "Gross motor",
        "Sommeil":"Sleep",
        "Epilepsie":"Seizure",
        "Comportement":"Behavior",
        "Aucune":"None"
    }

    # Fonction de nettoyage par mot
    mots = [mot.strip() for mot in texte.split(',')]
    mots_remplaces = [remplacements.get(mot, mot) for mot in mots]
    return ', '.join(mots_remplaces)

class T_DifficultiesSA(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeDifficultiesSA()
        return self.df

class T_DifficultiesSA_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeDifficultiesSA()
        self.df = _transformersDifficultiesSA_EN(self.df)
        return self.df

class T_MapFrance(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapFrance()
        self.df = _transformersMapFrance(self.df)
        return self.df

class T_MapFrance_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapFrance()
        self.df = _transformersMapFrance_EN(self.df)
        self.df['difficultesSA'] = self.df['difficultesSA'].apply(_transformDifficultiesSA)
        return self.df

class T_RegionsDepartements(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeRegionsDepartements("RegionDep")
        return self.df

class T_Regions(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeRegionsDepartements("Region")
        return self.df

class T_Capabilities(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeCapabilities()
        self.df = _transformersCapabilities(self.df)
        return self.df

if __name__ == "__main__":
    start = time.time()
    
    reader = T_DifficultiesSA()
    df = reader.readData()
    reader = T_MapFrance()
    df = reader.readData()
    reader = T_MapFrance_EN()
    df = reader.readData()
    reader = T_DifficultiesSA_EN()
    df = reader.readData()
    reader = T_RegionsDepartements()
    df = reader.readData()
    reader = T_Regions()
    df = reader.readData()
    reader = T_Capabilities()
    df = reader.readData()
    print(df.head())
    print(df.shape)
