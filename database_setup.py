import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch environment variables
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

def create_db():
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
    create_db()

