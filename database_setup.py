import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch environment variables
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

def create_database():
    try:
        # Connect to the default database
        conn = psycopg2.connect(dbname='postgres', user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        conn.autocommit = True
        c = conn.cursor()

        # Check if the database exists
        c.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [DB_NAME])
        exists = c.fetchone()

        # Create the database if it doesn't exist
        if not exists:
            c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"Database '{DB_NAME}' created successfully.")
        else:
            print(f"Database '{DB_NAME}' already exists.")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn is not None:
            conn.close()

def create_db_schema():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        conn.autocommit = True
        c = conn.cursor()

        # Drop table if it exists
        c.execute("DROP TABLE IF EXISTS attendance;")

        # Create the table with the new schema
        c.execute('''
        CREATE TABLE attendance (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            date DATE NOT NULL,
            jalali_date TEXT NOT NULL,
            day INTEGER NOT NULL,
            check_in TIME,
            check_out TIME
        );
        ''')

        print("Database schema created successfully.")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    create_database()
    create_db_schema()

