import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import exportBI.exportFrance as expFrance
import exportBI.exportLatam as expLatam
import exportBI.exportPoland as expPoland
import exportBI.exportSpain as expSpain
import exportBI.exportGlobal as expGlobal
import exportBI.exportAustralia as expAustralia
from utilsTools import export_Table
import time


def export_RegionsDepartements_French():
    """
    Method to read RegionsDepartements in French
    """
    reader = expFrance.T_RegionsDepartements()
    export_Table("T_MapFrance_RegionDepartement_French","France/createRegionDepartement_French.sql", reader)

def export_RegionsPrefectures_French():
    """
    Method to read RegionsPrefectures in French
    """
    reader = expFrance.T_Regions()
    export_Table("T_MapFrance_RegionPrefecture_French","France/createPrefectureRegion_French.sql", reader)

def export_DifficultiesSA_French():
    """
    Method to read DifficultiesSA in French
    """
    reader = expFrance.T_DifficultiesSA()
    export_Table("T_MapFrance_DifficultiesSA_French","France/createDifficultiesSA_French.sql", reader)

def export_DifficultiesSA_English():
    """
    Method to read DifficultiesSA in English
    """
    reader = expFrance.T_DifficultiesSA_EN()
    export_Table("T_MapFrance_DifficultiesSA_English","France/createDifficultiesSA_English.sql", reader)

def export_mapFrance_French():
    reader = expFrance.T_MapFrance()
    export_Table("T_MapFrance_French","France/createMapFrance_French.sql", reader)

def export_mapFrance_English():
    reader = expFrance.T_MapFrance_EN()
    export_Table("T_MapFrance_English","France/createMapFrance_English.sql", reader)

def export_capabilities_English():
    reader = expFrance.T_Capabilities()
    export_Table("T_MapFrance_Capabilitie","France/createCapabilities.sql", reader)

def export_mapLatam_Spanish():
    reader = expLatam.T_MapLatam()
    export_Table("T_MapLatam_Spanish","Latam/createMapLatam_Spanish.sql", reader)

def export_mapLatam_English():
    reader = expLatam.T_MapLatam_EN()
    export_Table("T_MapLatam_English","Latam/createMapLatam_English.sql", reader)

def export_mapPoland_Polish():
    reader = expPoland.T_MapPoland()
    export_Table("T_MapPoland_Polish","Poland/createMapPoland_Polish.sql", reader)

def export_mapPoland_English():
    reader = expPoland.T_MapPoland_EN()
    export_Table("T_MapPoland_English","Poland/createMapPoland_English.sql", reader)

def export_mapSpain_Spanish():
    reader = expSpain.T_MapSpain()
    export_Table("T_MapSpain_Spanish","Spain/createMapSpain_Spanish.sql", reader)

def export_mapSpain_English():
    reader = expSpain.T_MapSpain_EN()
    export_Table("T_MapSpain_English","Spain/createMapSpain_English.sql", reader)

def export_mapAustralia_English():
    reader = expAustralia.T_MapAustralia_EN()
    export_Table("T_MapAustralia_English","Australia/createMapAustralia_English.sql", reader)

def export_capabilities_Latam_English():
    reader = expLatam.T_Capabilities()
    export_Table("T_MapLatam_Capabilitie","Latam/createCapabilities.sql", reader)

def export_mapGlobal():
    reader = expGlobal.T_MapGlobal()
    export_Table("T_MapGlobal", "Global/createMapGlobal.sql", reader)

if __name__ == "__main__":
    """
    Endpoint to launch the different scrapers with injection of the results into the database 
    """
    start = time.time()

    export_DifficultiesSA_English()
    print("\n")
    export_capabilities_English()
    print("\n")
    export_mapFrance_French()
    print("\n")
    export_mapFrance_English()
    print("\n")
    export_RegionsDepartements_French()
    print("\n")
    export_RegionsPrefectures_French()
    print("\n")
    export_DifficultiesSA_French()
    
    export_mapLatam_Spanish()
    print("\n")
    export_mapLatam_English()
    print("\n")
    export_capabilities_Latam_English()
    print("\n")
    
    export_mapPoland_Polish()
    print("\n")
    export_mapPoland_English()
    print("\n")
    
    export_mapSpain_Spanish()
    print("\n")
    export_mapSpain_English()
    print("\n")

    export_mapAustralia_English()
    print("\n")
 
    export_mapGlobal()
    print("\n")
    
    print("\nExecute time : ", round(time.time()-start, 2), "s")