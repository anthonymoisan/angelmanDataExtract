import sys
import os
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract, BuildDataframeFromRegistry
  
def _buildDataframeMapSpain_EN():
    df = BuildDataframeFromRegistry("Spain")
    return df

def _transformersMapSpain_EN(df):
    df["sexe"] = df["sexe"].replace("Male", "M")
    df["sexe"] = df["sexe"].replace("Female", "F")
    df = df.rename(columns={"sexe": "gender"})    

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

def _transformersMapSpain(df):
    
    df["sexe"] = df["sexe"].replace("Male", "Hombre")
    df["sexe"] = df["sexe"].replace("Female", "Mujer")
    
    df["genotype"] = df["genotype"].replace("Uniparental disomy","Disomía uniparental UPD")
    df["genotype"] = df["genotype"].replace("Clinical","Clinical")
    df["genotype"] = df["genotype"].replace("NA","Lo perdio")
    df["genotype"] = df["genotype"].replace("Unknown","Lo perdio")
    df["genotype"] = df["genotype"].replace("Other","Lo perdio")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","Defecto en centro de impronta ICD")
    df["genotype"] = df["genotype"].replace("Deletion","Deleción")
    df["genotype"] = df["genotype"].replace("Mutation","Mutación")

    df.rename(columns={ "sexe" : "sexo", "genotype" : "genotipo", "age": "edad"},inplace=True)

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df

class T_MapSpain_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapSpain_EN()
        self.df = _transformersMapSpain_EN(self.df)
        return self.df

class T_MapSpain(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapSpain_EN()
        self.df = _transformersMapSpain(self.df)
        return self.df
    
if __name__ == "__main__":
  
    reader = T_MapSpain_EN()
    df = reader.readData()
    reader = T_MapSpain()
    df = reader.readData()
    print(df.head())
    print(df.shape)