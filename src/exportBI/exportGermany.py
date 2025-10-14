import sys
import os
import pandas as pd
import time
import os
from datetime import datetime
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract, BuildDataframeFromRegistry
  
def _buildDataframeMapGermany_EN():
    df = BuildDataframeFromRegistry("Germany")
    return df

def _transformersMapGermany_EN(df):
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

def _transformersMapGermany(df):
    df["sexe"] = df["sexe"].replace("Male", "Männlich")
    df["sexe"] = df["sexe"].replace("Female", "Weiblich")
    df["sexe"] = df["sexe"].replace("Indeterminate","Unbestimmt")

    df["genotype"] = df["genotype"].replace("Uniparental disomy","Uniparentale Disomie")
    df["genotype"] = df["genotype"].replace("Clinical","Klinisch")
    df["genotype"] = df["genotype"].replace("NA","Ich weiß nicht")
    df["genotype"] = df["genotype"].replace("Unknown","Ich weiß nicht")
    df["genotype"] = df["genotype"].replace("Other","Ich weiß nicht")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","Imprinting-Zentrum-Defekt")
    df["genotype"] = df["genotype"].replace("Deletion","Delezione")
    df["genotype"] = df["genotype"].replace("Mutation","Mutazione")

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df


class T_MapGermany_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapGermany_EN()
        self.df = _transformersMapGermany_EN(self.df)
        return self.df

class T_MapGermany(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapGermany_EN()
        self.df = _transformersMapGermany(self.df)
        return self.df
if __name__ == "__main__": 
    reader = T_MapGermany_EN()
    df = reader.readData()
    reader = T_MapGermany()
    df = reader.readData()
    print(df.head())
    print(df.shape)