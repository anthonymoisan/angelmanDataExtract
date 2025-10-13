# src/app/common/config.py
import os
from configparser import ConfigParser

# Détection PythonAnywhere vs local
LOCAL_CONNEXION = not os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower().startswith("pythonanywhere")

def load_db_config():
    """
    Lit ../angelman_viz_keys/Config2.ini (par rapport à src/app/)
    Retourne un dict avec les paramètres DB et SSH.
    """
    # __file__ = src/app/common/config.py
    app_dir = os.path.dirname(os.path.dirname(__file__))  # -> src/app
    cfg_path = os.path.join(app_dir, "..\..", "angelman_viz_keys", "Config2.ini")
    cfg_path = os.path.abspath(cfg_path)

    cfg = ConfigParser()
    if not cfg.read(cfg_path):
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    return {
        "LOCAL_CONNEXION": LOCAL_CONNEXION,
        "DB_HOST": cfg["MySQL"]["DB_HOST"],
        "DB_USERNAME": cfg["MySQL"]["DB_USERNAME"],
        "DB_PASSWORD": cfg["MySQL"]["DB_PASSWORD"],
        "DB_NAME": cfg["MySQL"]["DB_NAME"],
        "SSH_HOST": cfg["SSH"]["SSH_HOST"],
        "SSH_USERNAME": cfg["SSH"]["SSH_USERNAME"],
        "SSH_PASSWORD": cfg["SSH"]["SSH_PASSWORD"],
    }
