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
    
def _buildDataframeMapHungary():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Hungary']['SHEET_ID_HUNGARY']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Sheet1'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['Unique ID', 'Gender', 'DoB Y/M/D', 'AS Diagnosis', 'Greater Region', 'town']]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df.rename(columns={"Unique ID" : "internal_id", "Gender" : "gender", "DoB Y/M/D":"dateOfBirth", "AS Diagnosis" : "genotype", "Greater Region": "estate", "town" : "city", },inplace=True)

        return df


def _transformersMapHungary(df):
    df["gender"] = df["gender"].replace("male","M")
    df["gender"] = df["gender"].replace("female","F")
    
    
    df['dateOfBirth'] = pd.to_datetime(df['dateOfBirth'], format='%d/%m/%Y', errors='coerce')
    today = pd.to_datetime('today')
    df['age'] = df['dateOfBirth'].apply(
        lambda dob: today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )

    df["genotype"] = df["genotype"].replace("UBE3A mutation","Mutation")
    
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df['age'] = df['age'].fillna(0)
    df.drop(columns=["dateOfBirth" ],inplace=True)

    df["groupAge"] = pd.cut(
        df["age"],
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right = False
    )  
    return df


def _transformersMapHungary_HU(df):
    df["genotype"] = df["genotype"].replace("Deletion","törlés")
    df["genotype"] = df["genotype"].replace("Mutation","mutáció")
    df["genotype"] = df["genotype"].replace("UPD","szülői uniparentális diszómia")
    #df["genotype"] = df["genotype"].replace("ICD","βλάβη του κέντρου αποτύπωσης")
    #df["genotype"] = df["genotype"].replace("I don’t know","Δεν γνωρίζω")
    #df["genotype"] = df["genotype"].replace("Clinical","κλινική διάγνωση")
    
    df["gender"] = df["gender"].replace("M","férfi")
    df["gender"] = df["gender"].replace("F","nő")

    df["groupAge"] = df["groupAge"].replace("<4 years","életkor: 4 év alatt")
    df["groupAge"] = df["groupAge"].replace("4-8 years","életkor: 4–8 év")
    df["groupAge"] = df["groupAge"].replace("8-12 years","életkor: 8–12 év")
    df["groupAge"] = df["groupAge"].replace("12-17 years","életkor: 12–17 év")
    df["groupAge"] = df["groupAge"].replace(">18 years","életkor: 18 év felett")
    return df

class T_MapHungary_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapHungary()
        self.df = _transformersMapHungary(self.df)
        return self.df

class T_MapHungary_HU(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapHungary()
        self.df = _transformersMapHungary(self.df)
        self.df = _transformersMapHungary_HU(self.df)
        return self.df

if __name__ == "__main__":
  
    reader = T_MapHungary_HU()
    df = reader.readData()
    reader = T_MapHungary_EN()
    df = reader.readData()
    print(df.head())
    print(df.shape)
