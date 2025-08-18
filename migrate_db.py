from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3
from database import engine
from models import Base

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)
print("Created tables if they didn't exist")

# Connect to the database
conn = sqlite3.connect('./users.db')
cursor = conn.cursor()

# Add the missing columns
try:
    cursor.execute('ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0')
    print("Added is_verified column")
except sqlite3.OperationalError as e:
    print(f"Note: {e}")

try:
    cursor.execute('ALTER TABLE users ADD COLUMN verification_token STRING UNIQUE')
    print("Added verification_token column")
except sqlite3.OperationalError as e:
    print(f"Note: {e}")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database migration completed!")