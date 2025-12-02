import sys,os
import time
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[2]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from angelmanSyndromeConnexion import error
from angelmanSyndromeConnexion.pointRemarquable import insertPointRemarquable,getRecordsPointsRemarquables
from tools.logger import setup_logger
from tools.utilsTools import dropTable,createTable
# Set up logger
logger = setup_logger(debug=False)

def _insertDataFrame():
    
    points = [
    (2.337600, 48.860600, "Pyramide du Louvre (Paris)",
     "La cour Napoléon du musée du Louvre, et sa pyramide de verre."),
    (2.349900, 48.852970, "Notre-Dame de Paris",
     "Cathédrale gothique emblématique sur l’île de la Cité."),
    (2.295000, 48.873800, "Arc de Triomphe (Paris)",
     "Monument au sommet des Champs-Élysées."),
    (2.343100, 48.886700, "Basilique du Sacré-Cœur (Paris)",
     "Basilique blanche au sommet de Montmartre."),
    (5.370000, 43.296900, "Vieux-Port (Marseille)",
     "Port historique de Marseille, cœur de la ville."),
    (5.371300, 43.284100, "Notre-Dame de la Garde (Marseille)",
     "Basilique dominant Marseille, surnommée la Bonne Mère."),
    (4.821000, 45.762200, "Basilique de Fourvière (Lyon)",
     "Basilique sur la colline de Fourvière avec vue sur Lyon."),
    (-0.569200, 44.841000, "Place de la Bourse (Bordeaux)",
     "Célèbre façade XVIIIe et miroir d’eau sur la Garonne."),
    (7.265400, 43.695600, "Promenade des Anglais (Nice)",
     "Front de mer mythique longeant la baie des Anges."),
    (1.444000, 43.604500, "Place du Capitole (Toulouse)",
     "Grande place centrale et Capitole de Toulouse."),
    (7.750800, 48.581700, "Cathédrale de Strasbourg",
     "Cathédrale gothique en grès rose, flèche de 142 m."),
    (-1.553400, 47.217300, "Château des ducs de Bretagne (Nantes)",
     "Forteresse et musée d’histoire de Nantes."),
    (3.876700, 43.610800, "Place de la Comédie (Montpellier)",
     "Place centrale animée, opéra et cafés."),
    (3.063500, 50.636600, "Grand-Place (Lille)",
     "Grande place historique au cœur de Lille."),
    (-1.511500, 48.636100, "Mont-Saint-Michel",
     "Abbaye médiévale sur îlot rocheux en baie du Mont."),
    ]

    BASE = Path(__file__).resolve().parent / "../../.." / "data" / "Picture"

    img_path = BASE / "EiffelTower.jpg"
    photo_data = None
    try:
        if img_path.is_file():
            size = img_path.stat().st_size
            if size <= 4 * 1024 * 1024:
                with img_path.open("rb") as f:
                    photo_data = f.read()
            else:
                logger.error("Photo > 4MiB: %s", img_path)
        else:
            logger.warning("Fichier introuvable: %s", img_path)
    except Exception:
        logger.exception("Erreur lecture photo: %s", img_path)


    for lon, lat, sd, ld in points:
        insertPointRemarquable(lon, lat, sd, ld, photo_data)

def main():
    start = time.time()
    try:
        '''
        dropTable("T_PointRemarquable")
        wkdir = os.path.dirname(__file__)
        script_path = os.path.join(f"{wkdir}/../SQL/","createPointRemarquable.sql")
        createTable(script_path,bAngelmanResult=False)
        _insertDataFrame()
        '''
        df = getRecordsPointsRemarquables()
        logger.info(df.head())
        elapsed = time.time() - start
        
        logger.info(f"\n✅ Tables for Point Remarquable are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)
    except error.AppError as e:
        logger.critical("🚨 Error in the Point Remarquable process. %s : %s - %s",e.code, e.http_status, str(e))
        sys.exit(1)
    except Exception:
        logger.critical("🚨 Error in the Point Remarquable process.")
        sys.exit(1)

if __name__ == "__main__":
     main()