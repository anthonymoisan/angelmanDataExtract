import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import time
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract, BuildDataframeFromRegistry
  
def _buildDataframeMapFASTSpain_EN():
    df = BuildDataframeFromRegistry("Spain")
    return df

def _transformersMapFASTSpain_EN(df):
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
        bins=[0, 4, 8, 12, 17, 1000],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right=True
    )  

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df

def _transformersMapFASTSpain(df):
    
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

class T_MapFASTSpain_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapFASTSpain_EN()
        self.df = _transformersMapFASTSpain_EN(self.df)
        return self.df

class T_MapFASTSpain(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapFASTSpain_EN()
        self.df = _transformersMapFASTSpain(self.df)
        return self.df
    
if __name__ == "__main__":
  
    reader = T_MapFASTSpain_EN()
    df = reader.readData()
    reader = T_MapFASTSpain()
    df = reader.readData()
    print(df.head())
    print(df.shape)