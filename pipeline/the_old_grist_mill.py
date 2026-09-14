#!/usr/bin/env python
"""Ingest collector inventory from a GitHub Release CSV into Postgres.

Layout follows a small ETL job:
  1. config at the top (source, table, chunk size, DB from env)
  2. transform helpers applied to the full frame
  3. extract / load functions with one job each
  4. main() as the only orchestrator
"""

import logging
import os

import pandas as pd
from sqlalchemy import create_engine
from tqdm.auto import tqdm

# ---------------------------------------------------------------------------
# Config — change these without touching the pipeline logic
# ---------------------------------------------------------------------------

SOURCE_URL = (
    "https://github.com/rcm-webdev/docker-workshop/releases/download/v1/"
    "inventory_main_clean.csv.gz"
)
TABLE_NAME = "collector_vault_data"
CHUNK_SIZE = 500

POSTGRES_USER = os.getenv("POSTGRES_USER", "root")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "root")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "collector_vault")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transform — decide columns from the full file, then reuse that list
# ---------------------------------------------------------------------------

def columns_to_keep(df: pd.DataFrame) -> list[str]:
    """Return columns that have data and more than one distinct value."""
    df = df.dropna(axis=1, how="all")
    return [c for c in df.columns if df[c].nunique(dropna=True) > 1]


def apply_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Project a frame onto a fixed column list so chunks match the table."""
    return df.loc[:, columns]


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

def read_source(url: str) -> pd.DataFrame:
    """Read the full CSV so column cleanup sees every row, not a 100-row peek."""
    return pd.read_csv(url)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def make_engine():
    url = (
        f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    return create_engine(url)


def replace_table(engine, schema_df: pd.DataFrame, table_name: str) -> None:
    """Drop the table if it already exists, then create it empty from dtypes."""
    logger.info(pd.io.sql.get_schema(schema_df, name=table_name, con=engine))
    schema_df.head(n=0).to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False,
    )


def append_chunk(chunk: pd.DataFrame, engine, table_name: str) -> int:
    chunk.to_sql(name=table_name, con=engine, if_exists="append", index=False)
    return len(chunk)


# ---------------------------------------------------------------------------
# Orchestrate
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    df = read_source(SOURCE_URL)
    keep = columns_to_keep(df)
    df = apply_columns(df, keep)

    engine = make_engine()
    try:
        # Existing database is fine. This only replaces the destination table
        # so a rerun does not append onto an old, narrower schema.
        replace_table(engine, df, TABLE_NAME)

        rows_written = 0
        for start in tqdm(range(0, len(df), CHUNK_SIZE), desc=f"loading {TABLE_NAME}"):
            chunk = df.iloc[start : start + CHUNK_SIZE]
            rows_written += append_chunk(chunk, engine, TABLE_NAME)
            logger.info("appended %s rows", len(chunk))

        logger.info("finished: %s rows -> %s", rows_written, TABLE_NAME)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
