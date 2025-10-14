import sys
import os
import pandas as pd
import time
from configparser import ConfigParser
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract
    
def _buildDataframeMapIndonesia():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Indonesia']['SHEET_ID_MAP_INDONESIA']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'AS-IND'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[1]      # La première ligne devient les noms de colonnes
        df = df[2:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['DATE OF BIRTH', 'GENDER', 'CITY OF RESIDENCE', 'GENOTYPE']]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df.rename(columns={"DATE OF BIRTH" : "dateOfBirth", "GENDER" : "gender", "CITY OF RESIDENCE" : "city", "GENOTYPE" : "genotype"},inplace=True)

        return df


def _transformersMapIndonesia(df):
    df["gender"] = df["gender"].replace("Male","M")
    df["gender"] = df["gender"].replace("male","M")
    df["gender"] = df["gender"].replace("Female","F")
    df["gender"] = df["gender"].replace("female","F")

    
    #df["dateOfBirth"] = pd.to_datetime(df["dateOfBirth"], dayfirst=True).dt.strftime("%d/%m/%Y")

    df['dateOfBirth'] = pd.to_datetime(df['dateOfBirth'], format='%m/%d/%Y', errors='coerce')
    today = pd.to_datetime('today')
    df['age'] = df['dateOfBirth'].apply(
        lambda dob: today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )

    df["genotype"] = df["genotype"].replace("I don't know for the genotype","I don't know")

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

def _transformersMapIndonesia_IN(df):
    df["genotype"] = df["genotype"].replace("Deletion","Delesi")
    df["genotype"] = df["genotype"].replace("Mutation","Mutasi")
    df["genotype"] = df["genotype"].replace("UPD","Disomi orang tua tunggal")
    df["genotype"] = df["genotype"].replace("ICD","Kelainan pusat imprinting")
    df["genotype"] = df["genotype"].replace("I don't know","Tidak tahu")
    df["genotype"] = df["genotype"].replace("Clinical","Gejala klinis")
    
    df["gender"] = df["gender"].replace("M","Pria")
    df["gender"] = df["gender"].replace("F","Wanita")

    df["groupAge"] = df["groupAge"].replace("<4 years","< 4 tahun")
    df["groupAge"] = df["groupAge"].replace("4-8 years","4–8 tahun")
    df["groupAge"] = df["groupAge"].replace("8-12 years","8–12 tahun")
    df["groupAge"] = df["groupAge"].replace("12-17 years","12–17 tahun")
    df["groupAge"] = df["groupAge"].replace(">18 years",">18 tahun")
    return df

class T_MapIndonesia_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapIndonesia()
        self.df = _transformersMapIndonesia(self.df)
        return self.df

class T_MapIndonesia_IN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapIndonesia()
        self.df = _transformersMapIndonesia(self.df)
        self.df = _transformersMapIndonesia_IN(self.df)
        return self.df
        
if __name__ == "__main__":
  
    reader = T_MapIndonesia_EN()
    df = reader.readData()
    reader = T_MapIndonesia_IN()
    df = reader.readData()
    print(df.head())
    print(df.shape)
