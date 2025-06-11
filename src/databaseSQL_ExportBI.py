import time
import exportBI.exportFASTFrance as expFASTFrance
import exportBI.exportFASTLatam as expFASTLatam
import exportBI.exportFASTPoland as expFASTPoland
import exportBI.exportFASTSpain as expFASTSpain
import exportBI.exportFASTGlobal as expFASTGlobal
from utilsTools import export_Table

def export_RegionsDepartements_French():
    """
    Method to read RegionsDepartements in French
    """
    reader = expFASTFrance.T_RegionsDepartements()
    export_Table("T_FAST_France_RegionDepartement_French","FAST France/createRegionDepartement_French.sql", reader)

def export_RegionsPrefectures_French():
    """
    Method to read RegionsPrefectures in French
    """
    reader = expFASTFrance.T_Regions()
    export_Table("T_FAST_France_RegionPrefecture_French","FAST France/createPrefectureRegion_French.sql", reader)

def export_DifficultiesSA_French():
    """
    Method to read DifficultiesSA in French
    """
    reader = expFASTFrance.T_DifficultiesSA()
    export_Table("T_FAST_France_DifficultiesSA_French","FAST France/createDifficultiesSA_French.sql", reader)

def export_DifficultiesSA_English():
    """
    Method to read DifficultiesSA in English
    """
    reader = expFASTFrance.T_DifficultiesSA_EN()
    export_Table("T_FAST_France_DifficultiesSA_English","FAST France/createDifficultiesSA_English.sql", reader)

def export_mapFrance_French():
    reader = expFASTFrance.T_MapFASTFrance()
    export_Table("T_FAST_France_MapFrance_French","FAST France/createMapFrance_French.sql", reader)

def export_mapFrance_English():
    reader = expFASTFrance.T_MapFASTFrance_EN()
    export_Table("T_FAST_France_MapFrance_English","FAST France/createMapFrance_English.sql", reader)

def export_capabilities_English():
    reader = expFASTFrance.T_Capabilities()
    export_Table("T_FAST_France_Capabilitie","FAST France/createCapabilities.sql", reader)

def export_mapLatam_Spanish():
    reader = expFASTLatam.T_MapFASTLatam()
    export_Table("T_FAST_Latam_MapLatam_Spanish","FAST Latam/createMapFASTLatam_Spanish.sql", reader)

def export_mapLatam_English():
    reader = expFASTLatam.T_MapFASTLatam_EN()
    export_Table("T_FAST_Latam_MapLatam_English","FAST Latam/createMapFASTLatam_English.sql", reader)

def export_mapPoland_Polish():
    reader = expFASTPoland.T_MapFASTPoland()
    export_Table("T_FAST_Poland_MapPoland_Polish","FAST Poland/createMapFASTPoland_Polish.sql", reader)

def export_mapPoland_English():
    reader = expFASTPoland.T_MapFASTPoland_EN()
    export_Table("T_FAST_Poland_MapPoland_English","FAST Poland/createMapFASTPoland_English.sql", reader)

def export_mapSpain_Spanish():
    reader = expFASTSpain.T_MapFASTSpain()
    export_Table("T_FAST_Spain_MapSpain_Spanish","FAST Spain/createMapFASTSpain_Spanish.sql", reader)

def export_mapSpain_English():
    reader = expFASTSpain.T_MapFASTSpain_EN()
    export_Table("T_FAST_Spain_MapSpain_English","FAST Spain/createMapFASTSpain_English.sql", reader)

def export_capabilities_Latam_English():
    reader = expFASTLatam.T_Capabilities()
    export_Table("T_FAST_Latam_Capabilitie","FAST Latam/createCapabilities.sql", reader)

def export_mapGlobal():
    reader = expFASTGlobal.T_MapFASTGlobal()
    export_Table("T_MapGlobal", "MAP Global/createMapGlobal.sql", reader)

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
    
    export_mapGlobal()
    print("\n")
    
    print("\nExecute time : ", round(time.time()-start, 2), "s")