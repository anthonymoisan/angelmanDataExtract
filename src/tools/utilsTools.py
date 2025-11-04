# utilsTools.py
import os
import time
import smtplib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
from configparser import ConfigParser
from email.message import EmailMessage
from datetime import datetime
import logging
from tools.logger import setup_logger
from tools.crypto_utils import encrypt_dataframe_auto

# ----- Logger -----
logger = setup_logger(debug=True)

# ----- Config paths -----
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "../../angelman_viz_keys/Config2.ini")
CONFIG_GMAIL_PATH = os.path.join(BASE_DIR, "../../angelman_viz_keys/Config4.ini")
SQL_DIR = os.path.join(BASE_DIR, "../SQLScript")
# Détection du contexte (local vs PythonAnywhere)
LOCAL_CONNEXION = not os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower().startswith("pythonanywhere")

# ----- Config helpers -----
def load_config(filepath: str) -> ConfigParser:
    config = ConfigParser()
    if config.read(filepath):
        return config
    raise FileNotFoundError(f"Config file not found: {filepath}")

def get_db_params(bAngelmanResult=True):
    cfg = load_config(CONFIG_PATH)
    if(bAngelmanResult):
        return {
            "ssh_host": cfg['SSH']['SSH_HOST'],
            "ssh_user": cfg['SSH']['SSH_USERNAME'],
            "ssh_pass": cfg['SSH']['SSH_PASSWORD'],
            "db_host":  cfg['MySQL']['DB_HOST'],
            "db_user":  cfg['MySQL']['DB_USERNAME'],
            "db_pass":  cfg['MySQL']['DB_PASSWORD'],
            "db_name":  cfg['MySQL']['DB_NAME'],
        }
    else:
        return {
            "ssh_host": cfg['SSH']['SSH_HOST'],
            "ssh_user": cfg['SSH']['SSH_USERNAME'],
            "ssh_pass": cfg['SSH']['SSH_PASSWORD'],
            "db_host":  cfg['MySQL']['DB_HOST'],
            "db_user":  cfg['MySQL']['DB_USERNAME'],
            "db_pass":  cfg['MySQL']['DB_PASSWORDAS'],
            "db_name":  cfg['MySQL']['DB_NAMEAS'],
        }
    
# ----- Email -----
def send_email_alert(title: str, message: str) -> None:
    cfg = load_config(CONFIG_GMAIL_PATH)
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = "fastfrancecontact@gmail.com"
    msg["To"] = "anthonymoisan@yahoo.fr"
    msg.set_content(message)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("fastfrancecontact", cfg['Gmail']['PASSWORD'])
            server.send_message(msg)
            logger.info("Email sent successfully.")
    except Exception as e:
        logger.error("Failed to send email: %s", e)

# ----- DB URL / Engine -----
def _build_db_url(params, local_port=None) -> str:
    host = "127.0.0.1" if local_port else params["db_host"]
    port = local_port if local_port else 3306
    return f"mysql+pymysql://{params['db_user']}:{params['db_pass']}@{host}:{port}/{params['db_name']}"

def _run_in_transaction_with_conn(worker_fn, *, max_retries=3, bAngelmanResult=True):
    """
    Exécute worker_fn(conn) dans UNE transaction/connexion.
    Retourne la valeur renvoyée par worker_fn.
    """
    cfg = get_db_params(bAngelmanResult)

    def _do(db_url: str):
        engine = create_engine(db_url, pool_pre_ping=True, future=True)
        try:
            with engine.begin() as conn:
                return worker_fn(conn)
        finally:
            engine.dispose()

    attempt = 0
    while attempt < max_retries:
        try:
            if LOCAL_CONNEXION:
                with SSHTunnelForwarder(
                    (cfg["ssh_host"]),
                    ssh_username=cfg["ssh_user"],
                    ssh_password=cfg["ssh_pass"],
                    remote_bind_address=(cfg["db_host"], 3306),
                ) as tunnel:
                    return _do(_build_db_url(cfg, tunnel.local_bind_port))
            else:
                return _do(_build_db_url(cfg))
        except Exception as e:
            attempt += 1
            logger.error("[Attempt %d] Transaction (worker) failed: %s", attempt, e)
            if attempt < max_retries:
                logger.info("Retrying in 3 seconds...")
                time.sleep(3)
            else:
                raise

'''
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, OperationalError

def _execute_sql(DATABASE_URL, query, *, return_result=False, scalar=False, params=None):
    """
    Exécute une requête SQLAlchemy text() ou str.
    - return_result=True -> fetchall()
    - scalar=True -> scalar_one_or_none() (ou scalar())
    """
    url = make_url(DATABASE_URL)
    safe_url = url._replace(password="***")  # masque le mdp dans les logs
    logger.debug("Creating engine for %s (dialect=%s, driver=%s)",
                 str(safe_url), url.get_backend_name(), url.get_driver_name())

    # Ajustements utiles selon le dialecte
    connect_args = {}
    engine_kwargs = dict(pool_pre_ping=True, future=True)
    if url.get_backend_name().startswith("sqlite"):
        connect_args["check_same_thread"] = False
        engine_kwargs.update(connect_args=connect_args)

    engine = create_engine(DATABASE_URL, **engine_kwargs)

    try:
        # Préflight: ouvre une connexion brute et ping le serveur
        with engine.connect() as conn:
            logger.debug("Connected. Running preflight ping...")
            try:
                conn.exec_driver_sql("SELECT 1")
            except Exception as ping_err:
                logger.error("Preflight ping failed: %r", ping_err)
                raise

        # Si ping OK, on peut ouvrir un begin() transactionnel
        with engine.begin() as conn:
            logger.debug("Transaction opened.")
            stmt = text(query) if isinstance(query, str) else query
            res = conn.execute(stmt, params or {})
            if scalar:
                try:
                    return res.scalar_one_or_none()
                except Exception:
                    return res.scalar()
            if return_result:
                return res.fetchall()
            return None

    except OperationalError as e:
        # Erreurs réseau/auth/SSL/limites de connexions
        logger.error("OperationalError on %s: %s | orig=%r", str(safe_url), e, getattr(e, "orig", None))
        raise
    except DBAPIError as e:
        # Erreurs DBAPI génériques (driver)
        logger.error("DBAPIError on %s: %s | orig=%r", str(safe_url), e, getattr(e, "orig", None))
        raise
    except Exception as e:
        logger.error("Execution error on %s: %s", str(safe_url), e)
        raise
    finally:
        try:
            engine.dispose()
            logger.debug("Database connection closed.")
        except Exception as e:
            logger.warning("Dispose failed: %r", e)
'''

def _execute_sql(DATABASE_URL, query, *, return_result=False, scalar=False, params=None):
    """
    Exécute une requête SQLAlchemy text() ou str.
    - return_result=True -> fetchall()
    - scalar=True -> scalar_one_or_none() (ou scalar())
    """
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    try:
        with engine.begin() as conn:
            logger.debug("Connected to database.")
            stmt = text(query) if isinstance(query, str) else query
            res = conn.execute(stmt, params or {})
            if scalar:
                # SQLAlchemy 1.4/2.0 compat
                try:
                    return res.scalar_one_or_none()
                except Exception:
                    return res.scalar()
            if return_result:
                return res.fetchall()
            return None
    except Exception as e:
        logger.error("Execution error: %s", e)
        raise
    finally:
        engine.dispose()
        logger.debug("Database connection closed.")


def _insert_df(DATABASE_URL, table_name, df, if_exists='replace'):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    try:
        with engine.begin() as conn:
            df.to_sql(table_name, con=conn, if_exists=if_exists, index=False)
            logger.info("Inserted values into %s", table_name)
    except Exception as e:
        logger.error("Insert error: %s", e)
        raise
    finally:
        engine.dispose()

# ----- Public helpers -----
def _run_query(query, *, return_result=False, scalar=False, max_retries=3, params=None, bAngelmanResult=True):
    """
    Exécute une requête avec gestion du tunnel SSH si nécessaire.
    - params: dict des bind params
    - return_result: fetchall()
    - scalar: scalar()
    """
    cfg = get_db_params(bAngelmanResult)
    attempt = 0
    while attempt < max_retries:
        try:
            if LOCAL_CONNEXION:
                with SSHTunnelForwarder(
                    (cfg["ssh_host"]),
                    ssh_username=cfg["ssh_user"],
                    ssh_password=cfg["ssh_pass"],
                    remote_bind_address=(cfg["db_host"], 3306),
                ) as tunnel:
                    db_url = _build_db_url(cfg, tunnel.local_bind_port)
                    return _execute_sql(db_url, query, return_result=return_result, scalar=scalar, params=params)
            else:
                db_url = _build_db_url(cfg)
                return _execute_sql(db_url, query, return_result=return_result, scalar=scalar, params=params)
        except Exception as e:
            attempt += 1
            logger.error("[Attempt %d] Query failed: %s", attempt, e)
            if attempt < max_retries:
                logger.info("Retrying in 3 seconds...")
                time.sleep(3)
            else:
                raise

def _insert_data(df, table_name, if_exists='replace',bAngelmanResult=True):
    cfg = get_db_params(bAngelmanResult)
    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            if LOCAL_CONNEXION:
                with SSHTunnelForwarder(
                    (cfg["ssh_host"]),
                    ssh_username=cfg["ssh_user"],
                    ssh_password=cfg["ssh_pass"],
                    remote_bind_address=(cfg["db_host"], 3306),
                ) as tunnel:
                    db_url = _build_db_url(cfg, tunnel.local_bind_port)
                    return _insert_df(db_url, table_name, df, if_exists)
            else:
                db_url = _build_db_url(cfg)
                return _insert_df(db_url, table_name, df, if_exists)
        except Exception as e:
            attempt += 1
            logger.error("[Attempt %d] Insert failed: %s", attempt, e)
            if attempt < max_retries:
                logger.info("Retrying insert in 3 seconds...")
                time.sleep(3)
            else:
                logger.error("Insert failed after %d attempts")
                raise

# ----- update_log utilitaires -----
def _create_update_log_table_if_not_exists(bAngelmanResult=True):
    query = """
    CREATE TABLE IF NOT EXISTS update_log (
      table_name VARCHAR(255) PRIMARY KEY,
      updated_at DATETIME
    )
    """
    _run_query(query,bAngelmanResult=bAngelmanResult)
    logger.info("Create Table `update_log` if not exists.")

def _log_table_update(table_name: str,bAngelmanResult:bool):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info("Trying to log update for %s at %s", table_name, now)

    # Vérifie si la ligne existe
    exists_sql = text("""
        SELECT COUNT(*) FROM update_log WHERE table_name = :t
    """)
    count = _run_query(exists_sql, scalar=True, params={"t": table_name},bAngelmanResult=bAngelmanResult) or 0

    if count == 0:
        insert_sql = text("""
            INSERT INTO update_log (table_name, updated_at)
            VALUES (:t, :ts)
        """)
        _run_query(insert_sql, params={"t": table_name, "ts": now}, bAngelmanResult=bAngelmanResult)
        logger.info("Inserted new row for %s in update_log.", table_name)
    else:
        update_sql = text("""
            UPDATE update_log SET updated_at = :ts WHERE table_name = :t
        """)
        _run_query(update_sql, params={"ts": now, "t": table_name},bAngelmanResult=bAngelmanResult)
        logger.info("Updated row for %s in update_log.", table_name)

# ----- Export générique -----
def export_Table(table_name, sql_script, reader, encrypt=True, bAngelmanResult=True):
    """
    - reader.readData() -> DataFrame
    - sql_script: nom de fichier SQL à exécuter pour (re)créer la table
    """
    try:
        start = time.time()
        logger.info("--- Reading data for %s", table_name)
        df = reader.readData()

        # Normalisations simples
        df = df.replace([np.inf, -np.inf], np.nan)
        # pandas >= 2 : categories -> object avant to_sql
        for col in df.columns:
            if pd.api.types.is_categorical_dtype(df[col]):
                df[col] = df[col].astype('object')

        # Remplissages
        for col in df.columns:
            if pd.api.types.is_float_dtype(df[col]):
                df[col] = df[col].fillna(0.0)
            elif pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].fillna("None")

        current_count = int(df.shape[0])

        # Table existe ?
        table_exists = bool(
            _run_query(
                text("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = DATABASE() AND table_name = :t
                """),
                scalar=True,
                params={"t": table_name},
                bAngelmanResult=bAngelmanResult
            ) or 0
        )

        previous_count = 0
        if table_exists:
            previous_count = int(
                _run_query(
                    text(f"SELECT COUNT(*) FROM `{table_name}`"),
                    scalar=True,
                    bAngelmanResult=bAngelmanResult
                ) or 0
            )

        if table_exists and current_count < 0.9 * previous_count:
            logger.warning("--- Data check failed. Keeping previous version.")
            send_email_alert(
                f"Alert about the Table {table_name}",
                f"Hi,\n\nWe decided to keep the previous database.\nCurrent Version lines: {current_count}\nPrevious Version Lines: {previous_count}",
            )
        else:
            logger.info("--- Data validated.")
            # (Re)crée la table à partir du script
            if table_exists:
                logger.info("--- Drop Table.")
                _run_query(text(f"DROP TABLE `{table_name}`"),bAngelmanResult=bAngelmanResult)

            script_path = os.path.join(SQL_DIR, sql_script)
            with open(script_path, "r", encoding="utf-8") as f:
                logger.info("--- Create Table.")
                _run_query(f.read(),bAngelmanResult=bAngelmanResult)

            if encrypt:
                encrypt_dataframe_auto(df, return_spec=True,inplace=True)
            logger.info("--- Insert data into Table.")
            _insert_data(df, table_name,bAngelmanResult=bAngelmanResult)

            _create_update_log_table_if_not_exists(bAngelmanResult=bAngelmanResult)
            logger.info("--- Update Log")
            _log_table_update(table_name,bAngelmanResult=bAngelmanResult)

            logger.info("Execution time for %s: %.2fs", table_name, time.time() - start)

    except Exception as e:
        logger.error("An error occurred in export_Table for %s: %s", table_name, e)
        raise

# ----- Debug -----
def _debug_database_name(DATABASE_URL):
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
        with engine.connect() as conn:
            db_name = conn.execute(text("SELECT DATABASE()")).scalar()
            logger.info("Connected to database: %s", db_name)
    except Exception as e:
        logger.error("Could not fetch database name: %s", e)
    finally:
        engine.dispose()

# ----- Lecture simple -----
def readTable(table_name: str,bAngelmanResult=True) -> pd.DataFrame:
    try:
        logger.info("Read Table %s", table_name)
        rows = _run_query(text(f"SELECT * FROM `{table_name}`"), return_result=True, bAngelmanResult=bAngelmanResult)
        if not rows:
            return pd.DataFrame()
        # Compat SQLAlchemy 1.4 / 2.0
        try:
            data = [row._mapping for row in rows]
        except AttributeError:
            data = [dict(row) for row in rows]
        return pd.DataFrame(data)
    except Exception as e:
        logger.error("Erreur lors de la lecture de la table %s: %s", table_name, e)
        return pd.DataFrame()

# -----------------------------
#  SQL helpers (DDL)
# -----------------------------
def createTable(script_path: str, bAngelmanResult=True):
    with open(script_path, "r", encoding="utf-8") as f:
        logger.info("--- Create Table.")
        _run_query(f.read(),bAngelmanResult=bAngelmanResult)

def dropTable(table_name: str, bAngelmanResult=True):
    safe_table = table_name.replace("`", "``")
    sql = text(f"DROP TABLE IF EXISTS `{safe_table}`")
    _run_query(sql,bAngelmanResult=bAngelmanResult)
