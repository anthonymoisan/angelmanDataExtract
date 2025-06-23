import sys
import os

# Ajoute src/ au chemin de recherche des modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilsTools import readTable
import pandas as pd
from exportBI.exportTools import T_ReaderAbstract
from configparser import ConfigParser

import time
import logging

from logger import setup_logger

# Set up logger
logger = setup_logger(debug=False)

# Get working directory
wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
config.read(filePath)
    

def readTable_with_retry(table_name, max_retries=3, delay_seconds=5):
    """
    Tentative de lecture avec relances automatiques
    """
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Tentative {attempt} de lecture de la table '{table_name}'")
            df = readTable(table_name)
            return df
        except Exception as e:
            logging.error(f"[ERREUR LECTURE] Table '{table_name}' - Tentative {attempt} : {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)
            else:
                logging.info(f"[ÉCHEC] Lecture de la table '{table_name}' échouée après {max_retries} tentatives.")
                return pd.DataFrame()

def safe_readTable(table_name, transformer):
    df = readTable_with_retry(table_name)
    return transformer(df)
    
def _buildDataFrameMapMapGlobal():
    df_France = safe_readTable("T_MapFrance_English", _transformersMapFrance)
    df_Latam = safe_readTable("T_MapLatam_English", _transformersMapLatam)
    df_Poland = safe_readTable("T_MapPoland_English", _transformersMapPoland)
    df_Spain = safe_readTable("T_MapSpain_English", _transformersMapSpain)
    df_Australia = safe_readTable("T_MapAustralia_English", _transformersMapAustralia)
    df_USA = safe_readTable("T_MapUSA_English", _transformersMapUSA)
    df_Canada = safe_readTable("T_MapCanada_English", _transformersMapCanada)
    df_UK = safe_readTable("T_MapUK_English", _transformersMapUK)
    df_Italy = safe_readTable("T_MapItaly_English", _transformersMapItaly)
    df_Germany = safe_readTable("T_MapGermany_English", _transformersMapGermany)
    df_Brazil = safe_readTable("T_MapBrazil_English", _transformersMapBrazil)
    df_total = pd.concat([df_France, df_Latam, df_Poland, df_Spain, df_Australia, df_USA, df_Canada, df_UK, df_Italy,df_Germany,df_Brazil], ignore_index=True)

    # Filtrage des valeurs valides uniquement si les colonnes existent
    if not df_total.empty:
        df_total = df_total[df_total["genotype"].isin(["Deletion", "Clinical", "Mutation", "UPD", "ICD", "Mosaic"])]
        df_total = df_total[df_total["gender"].isin(["M", "F"])] 
        df_total = df_total[pd.to_numeric(df_total["age"], errors="coerce").dropna().apply(float.is_integer)]


    return df_total


def _transformersMapFrance(df):
    df = df.rename(columns={"sexe": "gender"})
    df["country"] = "France"
    df = df[~df["code_Departement"].isin(["971", "972", "973", "974", "975", "976", "Maroc", "Algerie", "Belgique", "Canada", "Suisse", "Tunisie"])]
    df = df.drop(columns={'code_Departement','difficultesSA', 'annee'})
    df["linkDashboard"] = config['IdDashboard']['ID_FRENCH_ENGLISH']
    return df

def _transformersMapLatam(df):
    df = df.drop(columns={'city'})
    df["linkDashboard"] = config['IdDashboard']['ID_LATAM_ENGLISH']
    
    return df

def _transformersMapPoland(df):
    df = df.rename(columns={"sexe": "gender"})
    df["country"] = "Poland"
    df["linkDashboard"] = config['IdDashboard']['ID_POLAND_ENGLISH']
    return df    

def _transformersMapSpain(df):
    df["country"] = "Spain"
    df["linkDashboard"] = config['IdDashboard']['ID_SPAIN_ENGLISH']
    return df    

def _transformersMapAustralia(df):
    df["country"] = "Australia"
    df["linkDashboard"] = config['IdDashboard']['ID_AUSTRALIA_ENGLISH']
    return df

def _transformersMapUSA(df):
    df["country"] = "USA"
    df["linkDashboard"] = config['IdDashboard']['ID_USA_ENGLISH']
    return df

def _transformersMapCanada(df):
    df["country"] = "Canada"
    df["linkDashboard"] = config['IdDashboard']['ID_CANADA_ENGLISH']
    return df

def _transformersMapUK(df):
    df["country"] = "United Kingdom"
    df["linkDashboard"] = config['IdDashboard']['ID_UK_ENGLISH']
    return df

def _transformersMapItaly(df):
    df["country"] = "Italy"
    df["linkDashboard"] = config['IdDashboard']['ID_ITALY_ENGLISH']
    return df

def _transformersMapGermany(df):
    df["country"] = "Germany"
    df["linkDashboard"] = config['IdDashboard']['ID_GERMANY_ENGLISH']
    return df

def _transformersMapBrazil(df):
    df["country"] = "Brazil"
    df["linkDashboard"] = config['IdDashboard']['ID_GERMANY_ENGLISH']
    return df

class T_MapGlobal(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataFrameMapMapGlobal()
        return self.df
    
if __name__ == "__main__":
  
    reader = T_MapGlobal()
    df = reader.readData()
    logging.info(df.head())
    logging.info(df.shape)
    #print(df.dtypes)