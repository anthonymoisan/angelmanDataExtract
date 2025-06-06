import sys
import os

# Ajoute src/ au chemin de recherche des modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilsTools import readTable
import pandas as pd
from abc import ABC, abstractmethod

class T_ReaderAbstract(ABC):

    def __init__(self):
        self.df = pd.DataFrame()

    @abstractmethod
    def readData(self):
        pass

def _buildDataFrameMapMapGlobal():
    df_FAST_France = readTable("T_FAST_France_MapFrance_English")
    df_FAST_France = _transformersMapFASTFrance(df_FAST_France)
    df_FAST_Latam = readTable("T_FAST_Latam_MapLatam_English")
    df_FAST_Latam =  _transformersMapFASTLatam(df_FAST_Latam)
    df_total = pd.concat([df_FAST_France, df_FAST_Latam], ignore_index=True)
    return df_total

def _transformersMapFASTFrance(df):
    df = df.rename(columns={"sexe": "gender"})
    df["country"] = "France"
    df = df[~df["code_Departement"].isin(["971", "972", "973", "974", "975", "976", "Algerie", "Belgique", "Canada", "Suisse", "Tunisie"])]
    df = df.drop(columns={'code_Departement','difficultesSA', 'annee'})
    df["linkDashboard"] = "https://app.powerbi.com/groups/e021dfb0-ec0b-4e9b-aeee-89cd478700fc/reports/a3f644fe-4767-4ab6-a596-9a0ed63c8f9e/fdaf46ffd7a806123186?experience=power-bi"
    return df

def _transformersMapFASTLatam(df):
    df = df.drop(columns={'city'})
    df["linkDashboard"] = "https://app.powerbi.com/groups/b84b4375-5794-4a36-a6c8-6554b4e53de1/reports/17a3330d-e21b-4d9f-9515-f04a5a118edd/fdaf46ffd7a806123186?experience=power-bi"
    return df


class T_MapFASTGlobal(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataFrameMapMapGlobal()
        return self.df
    
if __name__ == "__main__":
  
    reader = T_MapFASTGlobal()
    df = reader.readData()
    print(df.head())
    print(df.shape)