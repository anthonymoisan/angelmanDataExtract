import sys
import os
import pandas as pd
import time
from configparser import ConfigParser
from datetime import date
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract
    
def _buildDataframeMapTurkey():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Turkey']['SHEET_ID_TURKEY']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Sayfa1'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['GENDER', 'DAY OF BIRTH','CITY', 'GENOTYPE']]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df.rename(columns={"GENDER" : "gender", "DAY OF BIRTH" : "dob", "CITY" : "city", "GENOTYPE" : "genotype"},inplace=True)

        return df


def _transformersMapTurkey(df):

    df["genotype"] = df["genotype"].replace("DELESYON","Deletion")
    df["genotype"] = df["genotype"].replace("MUTASYON","Mutation")
    df["genotype"] = df["genotype"].replace("UPD","UPD")
    df["genotype"] = df["genotype"].replace("ICD","ICD")
    df["genotype"] = df["genotype"].replace("MICRO DELESYON","Deletion")
    df["genotype"] = df["genotype"].replace("MOZAİK","Mozaic")
    df["gender"] = df["gender"].replace("MALE","M")
    df["gender"] = df["gender"].replace("GIRL","F")
    
    df['dob'] = pd.to_datetime(df["dob"], format="%d.%m.%Y")

    current_date = date.today()
    df["age"] = df["dob"].apply(lambda d: 
        current_date.year - d.year - ((current_date.month, current_date.day) < (d.month, d.day))
    )

    df["genotype"] = (
    df["genotype"].astype("string").str.strip()
      .replace(["", "None", "none", "nan", "NaN"], pd.NA)
      .fillna("I don't know")
    )

    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df['age'] = df['age'].fillna(0)
    df.drop(columns=["dob" ],inplace=True)

    df["groupAge"] = pd.cut(
        df["age"],
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right = False
    )  
    return df

def _transformersMapTurkey_TK(df):
    
    df["gender"] = df["gender"].replace("M","Erkek")
    df["gender"] = df["gender"].replace("F","Kadın")

    df["genotype"] = df["genotype"].replace("Deletion", "DELESYON")
    df["genotype"] = df["genotype"].replace("Mutation", "MUTASYON")
    df["genotype"] = df["genotype"].replace("UPD","UPD")
    df["genotype"] = df["genotype"].replace("ICD","ICD")
    df["genotype"] = df["genotype"].replace("I don't know","BILMIYORUM")
    df["genotype"] = df["genotype"].replace("Mozaic","MOZAİK")

    df["groupAge"] = df["groupAge"].replace("<4 years","4 yıldan küçük")
    df["groupAge"] = df["groupAge"].replace("4-8 years","4–8 yaş")
    df["groupAge"] = df["groupAge"].replace("8-12 years","8–12 yaş")
    df["groupAge"] = df["groupAge"].replace("12-17 years","12–17 yaş")
    df["groupAge"] = df["groupAge"].replace(">18 years","18 yaşından büyük")
    return df

class T_MapTurkey_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapTurkey()
        self.df = _transformersMapTurkey(self.df)
        return self.df

class T_MapTurkey_TK(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapTurkey()
        self.df = _transformersMapTurkey(self.df)
        self.df = _transformersMapTurkey_TK(self.df)
        return self.df
        
if __name__ == "__main__":
  
    reader = T_MapTurkey_EN()
    df = reader.readData()
    reader = T_MapTurkey_TK()
    df = reader.readData()
    print(df.head())
    print(df.shape)
