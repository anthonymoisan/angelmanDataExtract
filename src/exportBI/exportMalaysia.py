import sys
import os
import pandas as pd
import time
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract
    
def _buildDataframeMapMalaysia():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Malaysia']['SHEET_ID_MALAYSIA']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Sheet1'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['ID', 'GENDER', 'BIRTH YEAR','CITY', 'STATE', 'GENOTYPE']]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df.rename(columns={"ID" : "indexation", "GENDER" : "gender", "BIRTH YEAR" : "birthYear", "CITY" : "city", "STATE" : "states", "GENOTYPE" : "genotype"},inplace=True)

        return df


def _transformersMapMalaysia(df):
    df["gender"] = df["gender"].replace("MALE","M")
    df["gender"] = df["gender"].replace("FEMALE","F")
    
    df['birthYear'] = pd.to_numeric(df['birthYear'], errors='coerce')

    current_year = pd.Timestamp.today().year
    df['age'] = current_year - df['birthYear']

    df["genotype"] = df["genotype"].replace("DELETION","Deletion")
    df["genotype"] = df["genotype"].replace("DELETION & DUPLICATION","Deletion")
    df["genotype"] = df["genotype"].replace("UBE3A MUTATION","Mutation")
    df["genotype"] = df["genotype"].replace("UNKNOWN","I don't know")
    df["genotype"] = df["genotype"].replace("MOSAIC ANGELMAN SYNDROME","Mosaic")
    df["genotype"] = df["genotype"].replace("IMPRINTING CENTER DEFECT","ICD")

    df["genotype"] = (
    df["genotype"].astype("string").str.strip()
      .replace(["", "None", "none", "nan", "NaN"], pd.NA)
      .fillna("I don't know")
)

    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df['age'] = df['age'].fillna(0)
    df.drop(columns=["birthYear" ],inplace=True)

    df["groupAge"] = pd.cut(
        df["age"],
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right = False
    )  
    return df

def _transformersMapMalaysia_MA(df):
    df["genotype"] = df["genotype"].replace("Deletion","Pemadaman")
    df["genotype"] = df["genotype"].replace("Mutation","Mutasi")
    df["genotype"] = df["genotype"].replace("UPD","Disomi Ibu Bapa Tunggal")
    df["genotype"] = df["genotype"].replace("ICD","Kecacatan Pusat Pencetakan")
    df["genotype"] = df["genotype"].replace("I don't know","Kecacatan Pusat Pencetakan")
    df["genotype"] = df["genotype"].replace("Mosaic","Mozais")
    
    df["gender"] = df["gender"].replace("M","Lelaki")
    df["gender"] = df["gender"].replace("F","Perempuan")

    df["groupAge"] = df["groupAge"].replace("<4 years","<4 tahun")
    df["groupAge"] = df["groupAge"].replace("4-8 years","4–8 tahun")
    df["groupAge"] = df["groupAge"].replace("8-12 years","8–12 tahun")
    df["groupAge"] = df["groupAge"].replace("12-17 years","12–17 tahun")
    df["groupAge"] = df["groupAge"].replace(">18 years",">18 tahun")
    return df

class T_MapMalaysia_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapMalaysia()
        self.df = _transformersMapMalaysia(self.df)
        return self.df

class T_MapMalaysia_MA(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapMalaysia()
        self.df = _transformersMapMalaysia(self.df)
        self.df = _transformersMapMalaysia_MA(self.df)
        return self.df
        
if __name__ == "__main__":
  
    reader = T_MapMalaysia_EN()
    df = reader.readData()
    reader = T_MapMalaysia_MA()
    df = reader.readData()
    print(df.head())
    print(df.shape)
