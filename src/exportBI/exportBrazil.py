import sys
import os
import pandas as pd
import time
import os
from datetime import datetime
from pathlib import Path
from configparser import ConfigParser
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract, BuildDataframeFromRegistry
  
def _buildDataframeMapBrazil():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Brazil']['SHEET_ID_BRAZIL']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'portugues'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['Internal ID', 'Data de Nascimento','Gênero', 'Estado', 'Cidade','Região','Diagnóstico']]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df.rename(columns={"Internal ID" : "internal_id", "Data de Nascimento" : "data de nascimento", "Gênero" : "genero", "Estado" : "estado","Cidade":"cidade", "Região":"regiao","Diagnóstico": "diagnostico"},inplace=True)
        return df
    
def _transformersMapBrazil(df):
    
    df['data de nascimento'] = pd.to_datetime(df['data de nascimento'], format='%d/%m/%Y', errors='coerce')
    today = pd.to_datetime('today')
    df['idade'] = df['data de nascimento'].apply(
        lambda dob: today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )
    df["idade"] = pd.to_numeric(df["idade"], errors="coerce")

    df["groupAge"] = pd.cut(
        df["idade"],
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 anos", "4-8 anos", "8-12 anos", "12-17 anos", ">18 anos"],
        right = False
    )  

    df = df.drop(columns=['data de nascimento'])
    
    return df


def _transformersMapBrazil_EN(df):
    
    df.rename(columns={"idade" : "age", "genero" : "gender", "estado" : "estate","cidade":"city", "regiao":"region","diagnostico": "genotype"},inplace=True)
    
    df["gender"] = df["gender"].replace("Masculino", "M")
    df["gender"] = df["gender"].replace("Feminino", "F")

    df["genotype"] = df["genotype"].replace("Deleção","Deletion")
    df["genotype"] = df["genotype"].replace("Mutação","Mutation")
    df["genotype"] = df["genotype"].replace("Dissomia uniparental","UPD")
    df["genotype"] = df["genotype"].replace("Não sei","I don't know")
    df["genotype"] = df["genotype"].replace("Clínico","Clinical")
    df["genotype"] = df["genotype"].replace("Defeitos de imprinting","ICD")

    df["groupAge"] =  df["groupAge"].replace("<4 anos","<4 years")
    df["groupAge"] =  df["groupAge"].replace("4-8 anos","4-8 years")
    df["groupAge"] =  df["groupAge"].replace("8-12 anos","8-12 years")
    df["groupAge"] =  df["groupAge"].replace("12-17 anos","12-17 years")
    df["groupAge"] =  df["groupAge"].replace(">18 anos",">18 years")

    return df

class T_MapBrazil_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapBrazil()
        self.df = _transformersMapBrazil(self.df)
        self.df = _transformersMapBrazil_EN(self.df)
        return self.df

class T_MapBrazil(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapBrazil()
        self.df = _transformersMapBrazil(self.df)
        return self.df
if __name__ == "__main__": 
    reader = T_MapBrazil()
    df = reader.readData()
    reader = T_MapBrazil_EN()
    df = reader.readData()
    print(df.head())
    print(df.shape)