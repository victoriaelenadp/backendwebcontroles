import psycopg2
import pandas as pd
from typing import List

# Puedes mover esto a un .env más adelante
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "mev37nkpmg",
    "host": "localhost",
    "port": "5432",
}


def get_table_data_as_df(table_name: str) -> pd.DataFrame:
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        query = f'SELECT * FROM "{table_name}"'
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()
