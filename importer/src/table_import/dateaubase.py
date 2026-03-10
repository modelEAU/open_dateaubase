from typing import List
from urllib import parse

import pandas as pd
import pytz
import sqlalchemy
from sqlalchemy import create_engine, text

from table_import.tables import ValueTable


def connect_local(server: str, database: str) -> sqlalchemy.Engine:
    engine = create_engine(f'mssql+pyodbc://{server}:1433/{database}?driver=ODBC+Driver+17+for+SQL+Server', connect_args={'connect_timeout': 2}, fast_executemany=True)
    print(f'Local connection: {engine.url}')
    return engine


def connect_remote(server: str, database: str, login_file: str) -> sqlalchemy.Engine:
    with open(login_file) as f:
        username = f.readline().strip()
        password = parse.quote_plus(f.readline().strip())
    engine = create_engine(f'mssql+pyodbc://{username}:{password}@{server}:1433/{database}?driver=ODBC+Driver+17+for+SQL+Server', connect_args={'connect_timeout': 2}, fast_executemany=True)
    print(f'Remote connection: {engine.url}')
    with engine.connect():
        pass
    return engine


def get_last_value_id(db_engine: sqlalchemy.Engine) -> int:
    query = 'SELECT MAX(Value_ID) FROM dbo.value'
    with db_engine.connect() as conn:
        result = conn.execute(text(query)).fetchone()
    return result[0]


def get_last_value_id_for_variable(db_engine: sqlalchemy.Engine, meta_ID: int) -> int:
    query = f'SELECT TOP 1 Value_ID FROM dbo.value WHERE Metadata_ID = {meta_ID} ORDER BY [Timestamp] DESC'
    with db_engine.connect() as conn:
        result = conn.execute(text(query)).fetchone()
    return result[0] if result else 0


def get_last_timestamp_for_variable(db_engine: sqlalchemy.Engine, meta_ID: int) -> int:
    query = f'SELECT TOP 1 Timestamp FROM dbo.value WHERE Metadata_ID = {meta_ID} ORDER BY [Timestamp] DESC'
    with db_engine.connect() as conn:
        result = conn.execute(text(query)).fetchone()
    return result[0] if result else 0


def engine_runs(engine: sqlalchemy.Engine) -> bool:
    try:
        _ = get_last_value_id(engine)
    except sqlalchemy.exc.DBAPIError:
        return False
    else:
        return True


def send_to_db(df: ValueTable, db_engine: sqlalchemy.Engine) -> None:
    '''stores df in SQL table dbo.value'''
    with db_engine.begin() as conn:
        df.to_sql('value', con=conn, if_exists='append', index=False)


def unix_seconds_to_local_datetime(seconds: int, local_timezone: str="America/Montreal"):
    if local_timezone not in pytz.all_timezones:
        raise ValueError(f"Provided timezone is not a valid timezone name: {local_timezone}")
    return pd.to_datetime(seconds, unit='s', origin='unix').tz_localize("UTC").tz_convert(local_timezone).tz_localize(None)


def local_datetime_to_unix_seconds(date: pd.Timestamp, local_timezone: str="America/Montreal") -> float:
    if local_timezone not in pytz.all_timezones:
        raise ValueError(f"Provided timezone is not a valid timezone name: {local_timezone}")
    return date.tz_localize(local_timezone).tz_convert("UTC").timestamp()


def get_rodtox_data_from_db(engine: sqlalchemy.Engine, variable: str, start_time: float, end_time: float) -> pd.DataFrame:
    variable_id_lookup: dict[str, int] = {
        "DO": 204,
        "Temp": 205,
        "Status": 206
    }
    metadata_id = variable_id_lookup[variable]
    query = text(f"SELECT * from VALUE WHERE Metadata_ID={metadata_id} AND Timestamp BETWEEN {start_time} and {end_time} ORDER BY [Timestamp] ASC")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


if __name__ == "__main__":
    import pandas as pd
    engine = connect_remote("132.203.190.77\\DATEAUBASE", "dateaubase2020", "login.txt")
    start = pd.to_datetime("2022-09-20 12:00:00")
    start_timestamp = local_datetime_to_unix_seconds(start)

    end = pd.to_datetime("2022-09-20 13:00:00")
    end_timestamp = local_datetime_to_unix_seconds(end)

    for variable in ["DO", "Temp", "Status"]:
        df = get_rodtox_data_from_db(engine, variable, start_timestamp, end_timestamp)
        print(df.head())
        if not df.empty:
            first_timestamp = df["Timestamp"].iloc[0]
            last_timestamp = df["Timestamp"].iloc[-1]
            timestring_start = unix_seconds_to_local_datetime(first_timestamp)
            timestring_end = unix_seconds_to_local_datetime(last_timestamp)
            print(timestring_start, timestring_end)
