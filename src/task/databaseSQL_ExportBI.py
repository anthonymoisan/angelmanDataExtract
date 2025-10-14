import sys, os
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import exportBI.exportFrance as expFrance
import exportBI.exportLatam as expLatam
import exportBI.exportPoland as expPoland
import exportBI.exportSpain as expSpain
import exportBI.exportGlobal as expGlobal
import exportBI.exportAustralia as expAustralia
import exportBI.exportUSA as expUSA
import exportBI.exportCanada as expCanada
import exportBI.exportUK as expUK
import exportBI.exportItaly as expItaly
import exportBI.exportGermany as expGermany
import exportBI.exportBrazil as expBrazil
import exportBI.exportIndia as expIndia
import exportBI.exportIndonesia as expIndonesia
import exportBI.exportGreece as expGreece

from tools.utilsTools import export_Table, send_email_alert
import time
import logging
from tools.logger import setup_logger

# Set up logger
logger = setup_logger(debug=False)


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

def export_mapUSA_English():
    reader = expUSA.T_MapUSA_EN()
    export_Table("T_MapUSA_English","USA/createMapUSA_English.sql", reader)

def export_mapCanada_English():
    reader = expCanada.T_MapFASTCanada_EN()
    export_Table("T_MapCanada_English","Canada/createMapCanada_English.sql", reader)

def export_mapUK_English():
    reader = expUK.T_MapUK_EN()
    export_Table("T_MapUK_English","UK/createMapUK_English.sql", reader)

def export_mapItaly_English():
    reader = expItaly.T_MapItaly_EN()
    export_Table("T_MapItaly_English","Italy/createMapItaly_English.sql", reader)

def export_mapItaly_Italian():
    reader = expItaly.T_MapItaly()
    export_Table("T_MapItaly_Italian","Italy/createMapItaly_Italian.sql", reader)

def export_mapGermany_English():
    reader = expGermany.T_MapGermany_EN()
    export_Table("T_MapGermany_English","Germany/createMapGermany_English.sql", reader)

def export_mapGermany_Deutsch():
    reader = expGermany.T_MapGermany()
    export_Table("T_MapGermany_Deutsch","Germany/createMapGermany_Deutsch.sql", reader)

def export_mapBrazil_English():
    reader = expBrazil.T_MapBrazil_EN()
    export_Table("T_MapBrazil_English","Brazil/createMapBrazil_English.sql", reader)

def export_mapBrazil_Portuguese():
    reader = expBrazil.T_MapBrazil()
    export_Table("T_MapBrazil_Portuguese","Brazil/createMapBrazil_Portuguese.sql", reader)

def export_capabilities_Latam_English():
    reader = expLatam.T_Capabilities()
    export_Table("T_MapLatam_Capabilitie","Latam/createCapabilities.sql", reader)

def export_mapIndia_English():
    reader = expIndia.T_MapIndia_EN()
    export_Table("T_MapIndia_English", "India/createMapIndia_English.sql", reader)

def export_mapIndia_Hindi():
    reader = expIndia.T_MapIndia_IN()
    export_Table("T_MapIndia_Hindi", "India/createMapIndia_Hindi.sql", reader)

def export_mapIndonesia_English():
    reader = expIndonesia.T_MapIndonesia_EN()
    export_Table("T_MapIndonesia_English", "Indonesia/createMapIndonesia_English.sql", reader)

def export_mapIndonesia_Ind():
    reader = expIndonesia.T_MapIndonesia_IN()
    export_Table("T_MapIndonesia_Ind", "Indonesia/createMapIndonesia_Ind.sql", reader)

def export_mapGreece_English():
    reader = expGreece.T_MapGreece_EN()
    export_Table("T_MapGreece_English", "Greece/createMapGreece_English.sql", reader)

def export_mapGreece_Greek():
    reader = expGreece.T_MapGreece_GR()
    export_Table("T_MapGreece_Greek", "Greece/createMapGreece_Greek.sql", reader)

def export_mapGlobal():
    reader = expGlobal.T_MapGlobal()
    export_Table("T_MapGlobal", "Global/createMapGlobal.sql", reader)

def safe_export(export_func, label):
    try:
        logger.info(f"🟡 Export : {label}")
        export_func()
        logger.info(f"✅ Export OK : {label}\n")
    except Exception as e:
        logger.error(f"❌ Échec KO {label} : {e}")

def main():
    start = time.time()
    try:
        
        safe_export(export_DifficultiesSA_English, "DifficultiesSA EN")
        safe_export(export_capabilities_English, "Capabilities FR")
        safe_export(export_mapFrance_French, "Map France FR")
        safe_export(export_mapFrance_English, "Map France EN")
        safe_export(export_RegionsDepartements_French, "Départements FR")
        safe_export(export_RegionsPrefectures_French, "Préfectures FR")
        safe_export(export_DifficultiesSA_French, "DifficultiesSA FR")
        safe_export(export_mapLatam_Spanish, "Map Latam ES")
        safe_export(export_mapLatam_English, "Map Latam EN")
        safe_export(export_capabilities_Latam_English, "Capabilities Latam EN")

        '''
        safe_export(export_mapPoland_Polish, "Map Poland PL")
        safe_export(export_mapPoland_English, "Map Poland EN")
        safe_export(export_mapSpain_Spanish, "Map Spain ES")
        safe_export(export_mapSpain_English, "Map Spain EN")
        safe_export(export_mapAustralia_English, "Map Australia EN")
        safe_export(export_mapUSA_English, "Map USA EN")
        safe_export(export_mapCanada_English, "Map Canada EN")
        safe_export(export_mapUK_English, "Map UK EN")
        safe_export(export_mapItaly_English, "Map Italy EN")
        safe_export(export_mapItaly_Italian, "Map Italy IT")
        safe_export(export_mapGermany_English, "Map Germany EN")
        safe_export(export_mapGermany_Deutsch, "Map Germany DE")
        safe_export(export_mapBrazil_English, "Map Brazil EN")
        safe_export(export_mapBrazil_Portuguese, "Map Brazil PT")
        '''

        
        safe_export(export_mapIndia_English, "Map India EN")
        safe_export(export_mapIndia_Hindi, "Map India HI")
        safe_export(export_mapIndonesia_English, "Map Indonesia EN")
        safe_export(export_mapIndonesia_Ind, "Map Indonesia IN")
        
        safe_export(export_mapGreece_English, "Map Greece EN")
        safe_export(export_mapGreece_Greek, "Map Greece GR")
        safe_export(export_mapGlobal, "Map Global")
        elapsed = time.time() - start
        logger.info(f"\n✅ All exports are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)

    except Exception:
        logger.critical("🚨 Error in the export process.")
        title = "Error in the export process BI"
        message = "Export BI KO. Check the log"
        send_email_alert(title, message)
        sys.exit(1)

if __name__ == "__main__":
     main()
    