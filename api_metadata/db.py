import pyodbc
import os
from dotenv import load_dotenv

# Charge les variables depuis .env
load_dotenv()

def get_connection():
    server = os.getenv("DB_SERVER")
    db_name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([server, db_name, user, password]):
        missing = [k for k, v in {
            "DB_SERVER": server,
            "DB_NAME": db_name,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items() if not v]
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={db_name};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)
