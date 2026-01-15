from dotenv import load_dotenv
import os
from mysql.connector import pooling

# Load .env variables
load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE")
}

# Init db - reduced pool_size for PythonAnywhere free tier (max 6 connections)
pool = pooling.MySQLConnectionPool(pool_name="pool", pool_size=2, **DB_CONFIG)
def get_conn():
    return pool.get_connection()

# DB-Helper
def db_read(sql, params=None, single=False):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())

        if single:
            # liefert EIN Dict oder None
            row = cur.fetchone()
            print("db_read(single=True) ->", row)   # DEBUG
            return row
        else:
            # liefert Liste von Dicts (evtl. [])
            rows = cur.fetchall()
            print("db_read(single=False) ->", rows)  # DEBUG
            return rows

    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()


def db_write(sql, params=None, return_id=False):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        print("db_write OK:", sql, params)  # DEBUG
        if return_id:
            return cur.lastrowid
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()