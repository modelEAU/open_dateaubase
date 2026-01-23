import pyodbc
import os
from dotenv import load_dotenv


if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

def get_connection():
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "1433")
    db_name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([host, db_name, user, password]):
        missing = [k for k, v in {
            "DB_HOST": host,
            "DB_NAME": db_name,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items() if not v]
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}"
        )

    server = f"{host},{port}"

    conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={db_name};"
    f"UID={user};"
    f"PWD={password};"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=5;"
)


    return pyodbc.connect(conn_str)
if __name__ == "__main__":
    conn = get_connection()
    print("DB connection OK")
    conn.close()
