import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import time
from configparser import ConfigParser
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract
    
def _buildDataframeMapIndia():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['India']['SHEET_ID_MAP_INDIA']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Sheet1'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['DOB OF CHILD', 'GENDER OF CHILD', 'CITY', 'STATE', 'GENOTYPE (DELETION POSITIVE, MUTATION, ICD, UPD ETC' ]]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df.rename(columns={"DOB OF CHILD" : "dateOfBirth", "GENDER OF CHILD" : "gender", "CITY" : "city", "STATE" : "states", "GENOTYPE (DELETION POSITIVE, MUTATION, ICD, UPD ETC" : "genotype"},inplace=True)

        return df


def _transformersMapIndia(df):
    df["gender"] = df["gender"].replace("Male","M")
    df["gender"] = df["gender"].replace("male","M")
    df["gender"] = df["gender"].replace("Female","F")
    df["gender"] = df["gender"].replace("female","F")

    df['dateOfBirth'] = pd.to_datetime(df['dateOfBirth'], format='%d/%m/%Y', errors='coerce')
    today = pd.to_datetime('today')
    df['age'] = df['dateOfBirth'].apply(
        lambda dob: today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )
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

class T_MapIndia_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapIndia()
        self.df = _transformersMapIndia(self.df)
        return self.df

class T_MapIndia_IN(T_ReaderAbstract):

    def readData(self):
        '''
        self.df = _buildDataframeMapLatam()
        self.df = _transformersMapLatam(self.df)
        self.df = _transformersMapLatam_EN(self.df)
        return self.df
        '''

if __name__ == "__main__":
  
    reader = T_MapIndia_EN()
    df = reader.readData()
    print(df.head())
    print(df.shape)
    #print(df.dtypes)

    #resultat = df.groupby('Genotipo').size().reset_index(name='Nombre')
    #print(resultat)
