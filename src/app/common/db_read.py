# src/app/common/db_read.py
import pandas as pd
from sqlalchemy import create_engine
from flask import jsonify
from sshtunnel import SSHTunnelForwarder
from tools.crypto_utils import decrypt_dataframe_auto
# ⬇️ import absolu
from app.common.config import load_db_config

def _read_table_as_json(table_name: str,decrypt = True):
    cfg = load_db_config()

    if cfg["LOCAL_CONNEXION"]:
        with SSHTunnelForwarder(
            (cfg["SSH_HOST"]),
            ssh_username=cfg["SSH_USERNAME"],
            ssh_password=cfg["SSH_PASSWORD"],
            remote_bind_address=(cfg["DB_HOST"], 3306),
        ) as tunnel:
            local_port = tunnel.local_bind_port
            db_url = (
                f"mysql+pymysql://{cfg['DB_USERNAME']}:{cfg['DB_PASSWORD']}"
                f"@127.0.0.1:{local_port}/{cfg['DB_NAME']}"
            )
            return _read_json_from_engine(db_url, table_name, decrypt=decrypt)
    else:
        db_url = (
            f"mysql+pymysql://{cfg['DB_USERNAME']}:{cfg['DB_PASSWORD']}"
            f"@{cfg['DB_HOST']}/{cfg['DB_NAME']}"
        )
        return _read_json_from_engine(db_url, table_name, decrypt=decrypt)

def _read_json_from_engine(db_url: str, table_name: str, decrypt = True):
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    try:
        with engine.connect() as conn:
            df = pd.read_sql_table(table_name, conn)
            if decrypt:
                decrypt_dataframe_auto(df,inplace=True)
        df = df.fillna("None")
        return jsonify(df.to_dict(orient="records"))
    finally:
        engine.dispose()
