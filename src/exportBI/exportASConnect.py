import sys
import os
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from tools.utilsTools import readTable
import pandas as pd
import time
import logging
from tools.crypto_utils import decrypt_dataframe

from tools.logger import setup_logger
from configparser import ConfigParser
from exportBI.exportTools import T_ReaderAbstract
from angelmanSyndromeConnexion.geo_utils3 import country_name_from_iso2

# Set up logger
logger = setup_logger(debug=False)

def readTable_with_retry(table_name, max_retries=3, delay_seconds=5):
    """
    Tentative de lecture avec relances automatiques
    """
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Tentative {attempt} de lecture de la table '{table_name}'")
            df = readTable(table_name, bAngelmanResult=False)
            return df
        except Exception as e:
            logging.error(f"[ERREUR LECTURE] Table '{table_name}' - Tentative {attempt} : {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)
            else:
                logging.info(f"[ÉCHEC] Lecture de la table '{table_name}' échouée après {max_retries} tentatives.")
                return pd.DataFrame()
            
def _buildDataFrameMapASConnect():
    df_PeoplePublic = readTable_with_retry("T_People_Public")
    cols = ['id', 'country_code', 'age_years', 'created_at', 'city' , 'gender']
    df_PeoplePublic = df_PeoplePublic.loc[:, df_PeoplePublic.columns.intersection(cols)]
    
    df_PeopleIdentity = readTable_with_retry("T_People_Identity")
    cols = ['person_id','genotype']
    df_PeopleIdentity = df_PeopleIdentity.loc[:, df_PeopleIdentity.columns.intersection(cols)]
    df_PeopleIdentity = df_PeopleIdentity.rename(columns={"person_id": "id"})
    df_merged = pd.merge(
        df_PeoplePublic,
        df_PeopleIdentity,
        on='id',
        how='inner'   # inner, left, right, outer
    )

    return df_merged

def _transformersMapASConnect(df):
    df = decrypt_dataframe(df, spec={'genotype':'str'}, inplace = True)
    df["genotype"] = df["genotype"].replace("Délétion","Deletion")
    df["genotype"] = df["genotype"].replace("Mosaïque","Mosaic")
    df["genotype"] = df["genotype"].replace("Clinique","Clinical")

    df = df.rename(columns={"age_years": "age"})

    df["groupAge"] = pd.cut(
        df["age"],
        bins=[-0.1, 4, 8, 12, 18, 100],
        labels=["<4 years", "4-8 years", "8-12 years", "12-17 years", ">18 years"],
        right = False
    ) 

    df['dateCreation'] = df['created_at'].dt.date
    df = df.drop(columns={'created_at'})

    df["country"] = df["country_code"].map(
    lambda x: country_name_from_iso2(x, locale="en")
)

    return df
    

class T_MapASConnect(T_ReaderAbstract):

    def readData(self):
        self.df = _buildDataFrameMapASConnect()
        self.df = _transformersMapASConnect(self.df)
        return self.df

if __name__ == "__main__":
  
    reader = T_MapASConnect()
    df = reader.readData()
    logging.info(df.head())
    logging.info(df.shape)