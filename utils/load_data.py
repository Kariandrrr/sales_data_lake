import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    raise ValueError(
        "Error: Missing environment variables! "
        "Please check your local .env file in the project root."
    )

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data_csv")

csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]

print("=== Starting raw data ingestion into PostgreSQL ===")

for file_name in csv_files:
    file_path = os.path.join(DATA_DIR, file_name)

    table_name = (
        file_name.replace("olist_", "").replace("_dataset.csv", "").replace(".csv", "")
    )

    print(f"Reading file: {file_name}...")
    df = pd.read_csv(file_path)

    print(f"Writing {len(df)} rows into table '{table_name}'...")
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"✓ Table '{table_name}' successfully created and populated.\n")

print("=== Raw data ingestion to PostgreSQL completed successfully! ===")
