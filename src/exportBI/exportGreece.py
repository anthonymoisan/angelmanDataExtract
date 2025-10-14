import sys
import os
import pandas as pd
import time
from configparser import ConfigParser
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract
    
def _buildDataframeMapGreece():
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
    if config.read(filePath):
        spreadsheet_id = config['Greece']['SHEET_ID_MAP_GREECE']
        api_key = config['APIGoogleSheets']['KEY']
        sheet_name = 'Sheet1'
        sheet_data = get_google_sheet_data(spreadsheet_id,sheet_name, api_key)
        df = pd.DataFrame(sheet_data['values'])# Utiliser la première ligne comme en-têtes
        df.columns = df.iloc[0]      # La première ligne devient les noms de colonnes
        df = df[1:].reset_index(drop=True)  # Supprimer la première ligne devenue inutile
        df = df[['Date of Birth', 'Gender', 'City', 'Syndrome Genotype']]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        df.rename(columns={"Date of Birth" : "dateOfBirth", "Gender" : "gender", "City" : "city", "Syndrome Genotype" : "genotype"},inplace=True)

        return df


def _transformersMapGreece(df):
    df["gender"] = df["gender"].replace("Male","M")
    df["gender"] = df["gender"].replace("male","M")
    df["gender"] = df["gender"].replace("Female","F")
    df["gender"] = df["gender"].replace("female","F")

    
    df['dateOfBirth'] = pd.to_datetime(df['dateOfBirth'], format='%d/%m/%Y', errors='coerce')
    today = pd.to_datetime('today')
    df['age'] = df['dateOfBirth'].apply(
        lambda dob: today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    )

    df["genotype"] = df["genotype"].replace("Maternal Gene Mutation(UBE3A Mutation)","Mutation")
    df["genotype"] = df["genotype"].replace("Uniparental Disomy (UPD)","UPD")

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


def _transformersMapGreece_GR(df):
    df["genotype"] = df["genotype"].replace("Deletion","Deέλλειψηlesi")
    df["genotype"] = df["genotype"].replace("Mutation","παραλλαγή")
    df["genotype"] = df["genotype"].replace("UPD","μονογονεϊκή δυσομία")
    df["genotype"] = df["genotype"].replace("ICD","βλάβη του κέντρου αποτύπωσης")
    df["genotype"] = df["genotype"].replace("I don’t know.","Δεν γνωρίζω")
    df["genotype"] = df["genotype"].replace("Clinical","κλινική διάγνωση")
    
    df["gender"] = df["gender"].replace("M","Άνδρας")
    df["gender"] = df["gender"].replace("F","Γυναίκα")

    df["groupAge"] = df["groupAge"].replace("<4 years","< 4 ετών")
    df["groupAge"] = df["groupAge"].replace("4-8 years","4–8 ετών")
    df["groupAge"] = df["groupAge"].replace("8-12 years","8–12 ετών")
    df["groupAge"] = df["groupAge"].replace("12-17 years","12–17 ετών")
    df["groupAge"] = df["groupAge"].replace(">18 years",">18 ετών")
    return df

class T_MapGreece_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapGreece()
        self.df = _transformersMapGreece(self.df)
        return self.df

class T_MapGreece_GR(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapGreece()
        self.df = _transformersMapGreece(self.df)
        self.df = _transformersMapGreece_GR(self.df)
        return self.df

if __name__ == "__main__":
  
    reader = T_MapGreece_EN()
    df = reader.readData()
    reader = T_MapGreece_GR()
    df = reader.readData()
    print(df.head())
    print(df.shape)
