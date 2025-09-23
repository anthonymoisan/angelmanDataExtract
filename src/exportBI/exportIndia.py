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

    df["genotype"] = df["genotype"].replace("deletion positive","Deletion")
    df["genotype"] = df["genotype"].replace("Deletion positive","Deletion")
    df["genotype"] = df["genotype"].replace("Deletion Positive","Deletion")
    df["genotype"] = df["genotype"].replace("Uniparental Disonomy","UPD")
    df["genotype"] = (
    df["genotype"].astype("string").str.strip()
      .replace(["", "None", "none", "nan", "NaN"], pd.NA)
      .fillna("I don't know")
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

def _transformersMapIndia_IN(df):
    df["genotype"] = df["genotype"].replace("Deletion","विलोपन")
    df["genotype"] = df["genotype"].replace("Mutation","जीन उत्परिवर्तन")
    df["genotype"] = df["genotype"].replace("UPD","यूनिपेरेंटल डिसॉमी")
    df["genotype"] = df["genotype"].replace("ICD","इम्प्रिंटिंग केंद्र दोष")
    df["genotype"] = df["genotype"].replace("I don't know","मालूम नहीं")
    df["genotype"] = df["genotype"].replace("Clinical","नैदानिक")
    
    df["gender"] = df["gender"].replace("M","पुरुष")
    df["gender"] = df["gender"].replace("F","महिला")

    df["groupAge"] = df["groupAge"].replace("<4 years","4 वर्ष से कम")
    df["groupAge"] = df["groupAge"].replace("4-8 years","4–8 वर्ष")
    df["groupAge"] = df["groupAge"].replace("8-12 years","8–12 वर्ष")
    df["groupAge"] = df["groupAge"].replace("12-17 years","12–17 वर्ष")
    df["groupAge"] = df["groupAge"].replace(">18 years","> 18 वर्ष")
    return df

class T_MapIndia_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapIndia()
        self.df = _transformersMapIndia(self.df)
        return self.df

class T_MapIndia_IN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapIndia()
        self.df = _transformersMapIndia(self.df)
        self.df = _transformersMapIndia_IN(self.df)
        return self.df
        
if __name__ == "__main__":
  
    reader = T_MapIndia_EN()
    df = reader.readData()
    reader = T_MapIndia_IN()
    df = reader.readData()
    print(df.head())
    print(df.shape)
