import sqlite3
import time


DATABASE_NAME = "HOPS_prototype1.db"


def connect_db():  # Connect to SQL database
    retries = 5
    while retries:
        try:
            return sqlite3.connect(DATABASE_NAME, timeout=10)
        except sqlite3.OperationalError:
            retries -= 1
            time.sleep(1)  # Wait for 1 second before retrying
    raise sqlite3.OperationalError("Database is locked and all retries failed.")

