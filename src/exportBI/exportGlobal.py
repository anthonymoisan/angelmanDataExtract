import sys
import os

# Ajoute src/ au chemin de recherche des modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilsTools import readTable
import pandas as pd
from exportBI.exportTools import T_ReaderAbstract

import time
import logging

from logger import setup_logger

# Set up logger
logger = setup_logger(debug=False)

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

    df_total = pd.concat([df_France, df_Latam, df_Poland, df_Spain, df_Australia, df_USA, df_Canada, df_UK], ignore_index=True)

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
    df["linkDashboard"] = "https://app.powerbi.com/groups/e021dfb0-ec0b-4e9b-aeee-89cd478700fc/reports/a3f644fe-4767-4ab6-a596-9a0ed63c8f9e/fdaf46ffd7a806123186?experience=power-bi"
    return df

def _transformersMapLatam(df):
    df = df.drop(columns={'city'})
    df["linkDashboard"] = "https://app.powerbi.com/groups/b84b4375-5794-4a36-a6c8-6554b4e53de1/reports/17a3330d-e21b-4d9f-9515-f04a5a118edd/fdaf46ffd7a806123186?experience=power-bi"
    return df

def _transformersMapPoland(df):
    df = df.rename(columns={"sexe": "gender"})
    df["country"] = "Poland"
    df["linkDashboard"] = "https://app.powerbi.com/groups/04e96c79-6db1-468b-9211-5cad9a6be08f/reports/face6d1a-6581-46de-a4d5-73a6d4aff2e6/fdaf46ffd7a806123186?experience=power-bi"
    return df    

def _transformersMapSpain(df):
    df["country"] = "Spain"
    df["linkDashboard"] = "https://app.powerbi.com/groups/5dee59e6-0976-4d44-a23f-5cc6b6508f60/reports/81fe5a2a-36ad-46dd-bb48-8771730376bf/fdaf46ffd7a806123186?experience=power-bi"
    return df    

def _transformersMapAustralia(df):
    df["country"] = "Australia"
    df["linkDashboard"] = ""
    return df

def _transformersMapUSA(df):
    df["country"] = "USA"
    df["linkDashboard"] = ""
    return df

def _transformersMapCanada(df):
    df["country"] = "Canada"
    df["linkDashboard"] = ""
    return df

def _transformersMapUK(df):
    df["country"] = "United Kingdom"
    df["linkDashboard"] = ""
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