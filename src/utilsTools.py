import os
import time
import smtplib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
from configparser import ConfigParser
from email.message import EmailMessage

# SSH & DB configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../angelman_viz_keys/Config2.ini")
CONFIG_GMAIL_PATH = os.path.join(os.path.dirname(__file__), "../angelman_viz_keys/Config4.ini")
LOCAL_CONNEXION = True

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
            print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", e)

def _execute_sql(DATABASE_URL, query, return_result=False):
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            print("Connected to database.")
            result = conn.execute(text(query))
            if return_result:
                data = result.fetchall()
                return data[0][0] if data and len(data[0]) == 1 else data
    except Exception as e:
        print("Execution error:", e)
    finally:
        engine.dispose()
        print("Database connection closed.")

def _insert_df(DATABASE_URL, table_name, df):
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            df.to_sql(table_name, con=conn, if_exists='replace', index=False)
            print(f"Inserted values into {table_name}")
    except Exception as e:
        print("Insert error:", e)
    finally:
        engine.dispose()

def _build_db_url(params, local_port=None):
    host = "127.0.0.1" if local_port else params["db_host"]
    port = local_port if local_port else 3306
    return f"mysql+pymysql://{params['db_user']}:{params['db_pass']}@{host}:{port}/{params['db_name']}"

def _run_query(query, return_result=False):
    params = get_db_params()
    if LOCAL_CONNEXION:
        with SSHTunnelForwarder(
            (params["ssh_host"]),
            ssh_username=params["ssh_user"],
            ssh_password=params["ssh_pass"],
            remote_bind_address=(params["db_host"], 3306)
        ) as tunnel:
            db_url = _build_db_url(params, tunnel.local_bind_port)
            return _execute_sql(db_url, query, return_result)
    else:
        db_url = _build_db_url(params)
        return _execute_sql(db_url, query, return_result)

def _insert_data(df, table_name):
    params = get_db_params()
    if LOCAL_CONNEXION:
        with SSHTunnelForwarder(
            (params["ssh_host"]),
            ssh_username=params["ssh_user"],
            ssh_password=params["ssh_pass"],
            remote_bind_address=(params["db_host"], 3306)
        ) as tunnel:
            db_url = _build_db_url(params, tunnel.local_bind_port)
            _insert_df(db_url, table_name, df)
    else:
        db_url = _build_db_url(params)
        _insert_df(db_url, table_name, df)

def export_Table(table_name, sql_script, reader):
    try:
        start = time.time()
        print(f"--- Reading data for {table_name}")
        df = reader.readData()
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.astype({col: 'object' for col in df.select_dtypes(include='category').columns})
        df.fillna("None", inplace=True)
        current_count = df.shape[0]

        check_query = f"""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = '{table_name}'
        """
        table_exists = _run_query(check_query, return_result=True)

        previous_count = (
            _run_query(f"SELECT COUNT(*) FROM {table_name}", return_result=True)
            if table_exists else 0
        )

        if current_count < 0.9 * previous_count:
            print("--- Data check failed. Keeping previous version.")
            send_email_alert(table_name, previous_count, current_count)
        else:
            print("--- Data validated.")
            if previous_count > 0:
                _run_query(f"DROP TABLE {table_name}")
            script_path = os.path.join(os.path.dirname(__file__), "SQLScript", sql_script)
            with open(script_path, "r", encoding="utf-8") as file:
                _run_query(file.read())
            _insert_data(df, table_name)
            print(f"Execution time for {table_name}: {round(time.time() - start, 2)}s")
    except Exception as e:
        print(f"An error occurred in export_Table for {table_name}: {e}")

def readTable(table_name):
    try:
        query = f"SELECT * FROM {table_name}"
        rows = _run_query(query, return_result=True)

        # Si aucun résultat, retourne DataFrame vide
        if not rows:
            return pd.DataFrame()

        # Si Row SQLAlchemy, convertir chaque ligne en dict
        try:
            data = [row._mapping for row in rows]  # SQLAlchemy >= 1.4
        except AttributeError:
            data = [dict(row) for row in rows]  # fallback

        return pd.DataFrame(data)

    except Exception as e:
        print(f"Erreur lors de la lecture de la table {table_name} :", e)
        return pd.DataFrame()