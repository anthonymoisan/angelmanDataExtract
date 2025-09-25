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
from logger import setup_logger

# Set up logger
logger = setup_logger(debug=True)

# SSH & DB configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../angelman_viz_keys/Config2.ini")
CONFIG_GMAIL_PATH = os.path.join(os.path.dirname(__file__), "../angelman_viz_keys/Config4.ini")

# Détection automatique de l'environnement
LOCAL_CONNEXION = not os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower().startswith("pythonanywhere")

def load_config(filepath):
    config = ConfigParser()
    if config.read(filepath):
        return config
    else:
        raise FileNotFoundError(f"Config file not found: {filepath}")

def get_db_params():
    config = load_config(CONFIG_PATH)
    return {
        "ssh_host": config['SSH']['SSH_HOST'],
        "ssh_user": config['SSH']['SSH_USERNAME'],
        "ssh_pass": config['SSH']['SSH_PASSWORD'],
        "db_host": config['MySQL']['DB_HOST'],
        "db_user": config['MySQL']['DB_USERNAME'],
        "db_pass": config['MySQL']['DB_PASSWORD'],
        "db_name": config['MySQL']['DB_NAME']
    }

def send_email_alert(table_name, previous, current):
    config = load_config(CONFIG_GMAIL_PATH)
    msg = EmailMessage()
    msg["Subject"] = f"Alert about the Table {table_name}"
    msg["From"] = "fastfrancecontact@gmail.com"
    msg["To"] = "anthonymoisan@yahoo.fr"
    msg.set_content(
        f"Hi,\n\nWe decided to keep the previous database.\nCurrent Version lines: {current}\nPrevious Version Lines: {previous}"
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("fastfrancecontact", config['Gmail']['PASSWORD'])
            server.send_message(msg)
            logger.info("Email sent successfully.")
    except Exception as e:
        logger.error("Failed to send email: %s", e)

def send_email_alert(title, message):
    config = load_config(CONFIG_GMAIL_PATH)
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = "fastfrancecontact@gmail.com"
    msg["To"] = "anthonymoisan@yahoo.fr"
    msg.set_content(message)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("fastfrancecontact", config['Gmail']['PASSWORD'])
            server.send_message(msg)
            logger.info("Email sent successfully.")
    except Exception as e:
        logger.error("Failed to send email: %s", e)


def _execute_sql(DATABASE_URL, query, return_result=False, params = None):
    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as conn:
            logger.info("Connected to database.")
            stmt = text(query) if isinstance(query, str) else query
            result = conn.execute(stmt, params or {})
            if return_result:
                data = result.fetchall()
                return data
    except Exception as e:
        logger.error("Execution error: %s", e)
        raise
    finally:
        engine.dispose()
        logger.info("Database connection closed.")

def _insert_df(DATABASE_URL, table_name, df, if_exists='replace'):
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            df.to_sql(table_name, con=conn, if_exists=if_exists, index=False)
            logger.info("Inserted values into %s", table_name)
    except Exception as e:
        logger.error("Insert error: %s", e)
        raise
    finally:
        engine.dispose()

def _build_db_url(params, local_port=None):
    host = "127.0.0.1" if local_port else params["db_host"]
    port = local_port if local_port else 3306
    return f"mysql+pymysql://{params['db_user']}:{params['db_pass']}@{host}:{port}/{params['db_name']}"

def _run_query(query, return_result=False, max_retries=3, paramsSQL=None):
    params = get_db_params()
    attempt = 0
    while attempt < max_retries:
        try:
            if LOCAL_CONNEXION:
                with SSHTunnelForwarder(
                    (params["ssh_host"]),
                    ssh_username=params["ssh_user"],
                    ssh_password=params["ssh_pass"],
                    remote_bind_address=(params["db_host"], 3306)
                ) as tunnel:
                    db_url = _build_db_url(params, tunnel.local_bind_port)
                    return _execute_sql(db_url, query, return_result, paramsSQL)
            else:
                db_url = _build_db_url(params)
                return _execute_sql(db_url, query, return_result, paramsSQL)
        except Exception as e:
            attempt += 1
            logger.error("[Attempt %d] Query failed: %s", attempt, e)
            if attempt < max_retries:
                logger.info("Retrying in 3 seconds...")
                time.sleep(3)
            else:
                raise

def _insert_data(df, table_name,if_exists='replace'):
    params = get_db_params()
    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            if LOCAL_CONNEXION:
                with SSHTunnelForwarder(
                    (params["ssh_host"]),
                    ssh_username=params["ssh_user"],
                    ssh_password=params["ssh_pass"],
                    remote_bind_address=(params["db_host"], 3306)
                ) as tunnel:
                    db_url = _build_db_url(params, tunnel.local_bind_port)
                    return _insert_df(db_url, table_name, df,if_exists)

            else:
                db_url = _build_db_url(params)
                return _insert_df(db_url, table_name, df,if_exists)
        except Exception as e:
            attempt += 1
            logger.error("[Attempt %d] Insert failed: %s", attempt, e)
            if attempt < max_retries:
                logger.info("Retrying insert in 3 seconds...")
                time.sleep(3)
            else:
                logger.error("Insert failed after %d attempts", max_retries)
                raise


def _log_table_update(table_name):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Trying to log update for {table_name} at {now}")
    
    resultQuery = f"""
                    SELECT COUNT(*) FROM update_log 
                    WHERE table_name = '{table_name}'
                    """
    result = _run_query(resultQuery,return_result=True)
    if result == 0:
        insertQuery = f"""
                            INSERT INTO update_log (table_name, updated_at)
                            VALUES ('{table_name}', '{now}')
                        """
        _run_query(insertQuery)
        logger.info(f"Inserted new row for {table_name} in update_log.")
    else:
        updateQuery = f"""
                        UPDATE update_log 
                        SET updated_at = '{now}' WHERE table_name = '{table_name}'
                        """
        _run_query(updateQuery)
        logger.info(f"Updated row for {table_name} in update_log.")
        

def _create_update_log_table_if_not_exists():
    query = """
            CREATE TABLE IF NOT EXISTS update_log (
            table_name VARCHAR(255) PRIMARY KEY,
            updated_at DATETIME
            )
            """
    _run_query(query=query, return_result=False)
    logger.info("Create Table `update_log` if not exists.")
    

def export_Table(table_name, sql_script, reader):
    try:
        start = time.time()
        logger.info("--- Reading data for %s", table_name)
        df = reader.readData()
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.astype({col: 'object' for col in df.select_dtypes(include='category').columns})

        for col in df.columns:
            if df[col].dtype == 'float64':
                df[col] = df[col].fillna(0.0)
            elif df[col].dtype == 'object':
                df[col] = df[col].fillna("None")
            elif pd.api.types.is_categorical_dtype(df[col]):
                df[col] = df[col].fillna("None")

        current_count = df.shape[0]

        check_query = f"""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = '{table_name}'
        """
        table_exists = _run_query(check_query, return_result=True)

        previous_countSQL = (
            _run_query(f"SELECT COUNT(*) FROM {table_name}", return_result=True)
            if table_exists else 0
        )

        previous_count= int(previous_countSQL[0][0])

        #logger.info("type previous count :", type(previous_count))

        if current_count < 0.9 * previous_count:
            logger.warning("--- Data check failed. Keeping previous version.")
            send_email_alert(table_name, previous_count, current_count)
        else:
            logger.info("--- Data validated.")
            if table_exists:
                logger.info("--- Drop Table.")
                _run_query(f"DROP TABLE {table_name}")
            script_path = os.path.join(os.path.dirname(__file__), "SQLScript", sql_script)
            with open(script_path, "r", encoding="utf-8") as file:
                logger.info("--- Create Table.")
                _run_query(file.read())
            logger.info("--- Insert data into Table.")
            _insert_data(df, table_name)
            _create_update_log_table_if_not_exists()
            logger.info("--- Update Log")
            _log_table_update(table_name)

            logger.info("Execution time for %s: %.2fs", table_name, time.time() - start)
    except Exception as e:
        logger.error("An error occurred in export_Table for %s: %s", table_name, e)
        raise

def _debug_database_name(DATABASE_URL):
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            db_name = conn.execute(text("SELECT DATABASE()")).scalar()
            logger.info(f"Connected to database: {db_name}")
    except Exception as e:
        logger.error(f"Could not fetch database name: {e}")
    finally:
        engine.dispose()

def readTable(table_name):
    try:
        logger.info("Read Table %s", table_name)
        query = f"SELECT * FROM {table_name}"
        rows = _run_query(query, return_result=True)

        if not rows:
            return pd.DataFrame()

        try:
            data = [row._mapping for row in rows]
        except AttributeError:
            data = [dict(row) for row in rows]

        return pd.DataFrame(data)

    except Exception as e:
        logger.error("Erreur lors de la lecture de la table %s: %s", table_name, e)
        return pd.DataFrame()
