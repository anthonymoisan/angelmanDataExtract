import sys
import os
import pandas as pd
import time
import os
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract, BuildDataframeFromRegistry
  
def _buildDataframeMapItaly_EN():
    df = BuildDataframeFromRegistry("Italy")
    return df

def _transformersMapItaly_EN(df):
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

def _transformersMapItaly(df):
    df["sexe"] = df["sexe"].replace("Male", "Maschio")
    df["sexe"] = df["sexe"].replace("Female", "Femmina")
    df["sexe"] = df["sexe"].replace("Indeterminate","Indeterminato")

    df["genotype"] = df["genotype"].replace("Uniparental disomy","Disomia uniparentale")
    df["genotype"] = df["genotype"].replace("Clinical","Clinico")
    df["genotype"] = df["genotype"].replace("NA","Non lo so")
    df["genotype"] = df["genotype"].replace("Unknown","Non lo so")
    df["genotype"] = df["genotype"].replace("Other","Nie wiem")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","Difetto del centro di imprinting")
    df["genotype"] = df["genotype"].replace("Deletion","Delezione")
    df["genotype"] = df["genotype"].replace("Mutation","Mutazione")

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df


class T_MapItaly_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapItaly_EN()
        self.df = _transformersMapItaly_EN(self.df)
        return self.df

class T_MapItaly(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapItaly_EN()
        self.df = _transformersMapItaly(self.df)
        return self.df
if __name__ == "__main__": 
    reader = T_MapItaly_EN()
    df = reader.readData()
    reader = T_MapItaly()
    df = reader.readData()
    print(df.head())
    print(df.shape)