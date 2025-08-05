import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import time
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract,BuildDataframeFromRegistry
    
def _buildDataframeMapPoland_EN():
    df = BuildDataframeFromRegistry("Poland")
    return df

def _transformersMapPoland_EN(df):
    df["sexe"] = df["sexe"].replace("Male", "M")
    df["sexe"] = df["sexe"].replace("Female", "F")

    df["genotype"] = df["genotype"].replace("Uniparental disomy","UPD")
    df["genotype"] = df["genotype"].replace("NA","I don't know")
    df["genotype"] = df["genotype"].replace("Unknown","I don't know")
    df["genotype"] = df["genotype"].replace("Other","I don't know")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","ICD")

    df["age"] = pd.to_numeric(df["age"], errors="coerce")

    df["groupAge"] = pd.cut(
        df["age"],
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right = False
    )  

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df

def _transformersMapPoland(df):
    df["sexe"] = df["sexe"].replace("Male", "Mężczyzna")
    df["sexe"] = df["sexe"].replace("Female", "Kobieta")
    df["sexe"] = df["sexe"].replace("Indeterminate","Nieokreślona")

    df["genotype"] = df["genotype"].replace("Uniparental disomy","Disomia uniparentalna")
    df["genotype"] = df["genotype"].replace("Clinical","Diagnoza kliniczna")
    df["genotype"] = df["genotype"].replace("NA","Nie wiem")
    df["genotype"] = df["genotype"].replace("Unknown","Nie wiem")
    df["genotype"] = df["genotype"].replace("Other","Nie wiem")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","Defekt centrum imprintingu")
    df["genotype"] = df["genotype"].replace("Deletion","Delecja")
    df["genotype"] = df["genotype"].replace("Mutation","Mutacja")

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df

class T_MapPoland_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapPoland_EN()
        self.df = _transformersMapPoland_EN(self.df)
        return self.df

class T_MapPoland(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapPoland_EN()
        self.df = _transformersMapPoland(self.df)
        return self.df
    
if __name__ == "__main__":
  
    reader = T_MapPoland_EN()
    df = reader.readData()
    reader = T_MapPoland()
    df = reader.readData()
    print(df.head())
    print(df.shape)