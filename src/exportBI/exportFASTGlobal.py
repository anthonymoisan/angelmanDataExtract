import sys
import os

# Ajoute src/ au chemin de recherche des modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utilsTools import readTable
import pandas as pd
from exportBI.exportTools import T_ReaderAbstract


def _buildDataFrameMapMapGlobal():
    df_FAST_France = readTable("T_FAST_France_MapFrance_English")
    df_FAST_France = _transformersMapFASTFrance(df_FAST_France)
    df_FAST_Latam = readTable("T_FAST_Latam_MapLatam_English")
    df_FAST_Latam =  _transformersMapFASTLatam(df_FAST_Latam)
    df_FAST_Poland = readTable("T_FAST_Poland_MapPoland_English")
    df_FAST_Poland = _transformersMapFASTPoland(df_FAST_Poland)
    df_FAST_Spain = readTable("T_FAST_Spain_MapSpain_English")
    df_FAST_Spain = _transformersMapFASTSpain(df_FAST_Spain)
    df_FAST_Australia = readTable("T_FAST_Australia_MapAustralia_English")
    df_FAST_Australia = _transformersMapFASTAustralia(df_FAST_Australia)
    df_total = pd.concat([df_FAST_France, df_FAST_Latam, df_FAST_Poland, df_FAST_Spain, df_FAST_Australia], ignore_index=True)
    
    df_total = df_total[df_total["genotype"].isin(["Deletion", "Clinical", "Mutation", "UPD", "ICD", "Mosaic"])]
    df_total = df_total[df_total["gender"].isin(["M", "F"])] 
    return df_total

def _transformersMapFASTFrance(df):
    df = df.rename(columns={"sexe": "gender"})
    df["country"] = "France"
    df = df[~df["code_Departement"].isin(["971", "972", "973", "974", "975", "976", "Maroc", "Algerie", "Belgique", "Canada", "Suisse", "Tunisie"])]
    df = df.drop(columns={'code_Departement','difficultesSA', 'annee'})
    df["linkDashboard"] = "https://app.powerbi.com/groups/e021dfb0-ec0b-4e9b-aeee-89cd478700fc/reports/a3f644fe-4767-4ab6-a596-9a0ed63c8f9e/fdaf46ffd7a806123186?experience=power-bi"
    return df

def _transformersMapFASTLatam(df):
    df = df.drop(columns={'city'})
    df["linkDashboard"] = "https://app.powerbi.com/groups/b84b4375-5794-4a36-a6c8-6554b4e53de1/reports/17a3330d-e21b-4d9f-9515-f04a5a118edd/fdaf46ffd7a806123186?experience=power-bi"
    return df

def _transformersMapFASTPoland(df):
    df = df.rename(columns={"sexe": "gender"})
    df["country"] = "Poland"
    df["linkDashboard"] = "https://app.powerbi.com/groups/04e96c79-6db1-468b-9211-5cad9a6be08f/reports/face6d1a-6581-46de-a4d5-73a6d4aff2e6/fdaf46ffd7a806123186?experience=power-bi"
    return df    

def _transformersMapFASTSpain(df):
    df["country"] = "Spain"
    df["linkDashboard"] = "https://app.powerbi.com/groups/5dee59e6-0976-4d44-a23f-5cc6b6508f60/reports/81fe5a2a-36ad-46dd-bb48-8771730376bf/fdaf46ffd7a806123186?experience=power-bi"
    return df    

def _transformersMapFASTAustralia(df):
    df["country"] = "Australia"
    df["linkDashboard"] = ""
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
    #print(df.dtypes)