# database.py — SQLite Database Layer
# CSV ki jagah data SQLite database mein store hoga.
 
import sqlite3
import pandas as pd
import os
 
DB_PATH = "finance.db"
 
# ─── Create tables if not exist ──────────────────────────────────────────────
 
def init_db():
    """Create the transactions table if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            description TEXT,
            amount      REAL NOT NULL,
            type        TEXT
        )
    """)
    conn.commit()
    conn.close()
 
# ─── Load data from CSV into DB (only first time) ────────────────────────────
 
def seed_from_csv(csv_path: str = "transactions.csv"):
    """
    Import CSV data into SQLite database.
    Skips seeding if data already exists.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    if count == 0 and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        df.rename(columns={
            "Date": "date",
            "Description": "description",
            "Amount": "amount",
            "Type": "type"
        }, inplace=True)
        df.to_sql("transactions", conn, if_exists="append", index=False)
        print(f"✅ Seeded {len(df)} rows from {csv_path}")
    conn.close()
 
# ─── Read all transactions ────────────────────────────────────────────────────
 
def load_transactions() -> pd.DataFrame:
    """Load all transactions from SQLite into a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    df.rename(columns={
        "date": "Date",
        "description": "Description",
        "amount": "Amount",
        "type": "Type"
    }, inplace=True)
    return df
 
# ─── Insert new rows (from uploaded CSV) ─────────────────────────────────────
 
def insert_transactions(df: pd.DataFrame):
    """Insert a DataFrame of transactions into the database."""
    conn = sqlite3.connect(DB_PATH)
    insert_df = df.copy()
    insert_df.rename(columns={
        "Date": "date",
        "Description": "description",
        "Amount": "amount",
        "Type": "type"
    }, inplace=True)
    insert_df["date"] = insert_df["date"].astype(str)
    insert_df[["date", "description", "amount", "type"]].to_sql(
        "transactions", conn, if_exists="append", index=False
    )
    conn.close()
 
# ─── Clear all data ───────────────────────────────────────────────────────────
 
def clear_transactions():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
 
# ─── Bootstrap on import ──────────────────────────────────────────────────────
init_db()
seed_from_csv()