import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import time
import os
from datetime import datetime
from exportBI.exportTools import get_google_sheet_data, T_ReaderAbstract, BuildDataframeFromRegistry
  
def _buildDataframeMapBrazil_EN():
    df = BuildDataframeFromRegistry("Brazil")
    return df

def _transformersMapBrazil_EN(df):
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

def _transformersMapBrazil(df):
    df["sexe"] = df["sexe"].replace("Male", "Masculino")
    df["sexe"] = df["sexe"].replace("Female", "Feminino")
    df["sexe"] = df["sexe"].replace("Indeterminate","Indeterminado")

    df["genotype"] = df["genotype"].replace("Uniparental disomy","Disomia uniparental")
    df["genotype"] = df["genotype"].replace("Clinical","Clínico")
    df["genotype"] = df["genotype"].replace("NA","Não sei")
    df["genotype"] = df["genotype"].replace("Unknown","Não sei")
    df["genotype"] = df["genotype"].replace("Other","Não sei")
    df["genotype"] = df["genotype"].replace("Imprinting centre defect","Defeito no centro de imprinting")
    df["genotype"] = df["genotype"].replace("Deletion","Deleção")
    df["genotype"] = df["genotype"].replace("Mutation","Mutação")

    df = df.drop(columns=['country','monthJoin', 'yearJoin'])

    return df


class T_MapBrazil_EN(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataframeMapBrazil_EN()
        self.df = _transformersMapBrazil_EN(self.df)
        return self.df

class T_MapBrazil(T_ReaderAbstract):
    def readData(self):
        self.df = _buildDataframeMapBrazil_EN()
        self.df = _transformersMapBrazil(self.df)
        return self.df
if __name__ == "__main__": 
    reader = T_MapBrazil_EN()
    df = reader.readData()
    reader = T_MapBrazil()
    df = reader.readData()
    print(df.head())
    print(df.shape)