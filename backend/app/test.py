from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Table, inspect, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Supabase uses postgres:// but SQLAlchemy requires postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

SQLALCHEMY_DATABASE_URL = DATABASE_URL or "sqlite:///../notes.db"

if "postgresql" in SQLALCHEMY_DATABASE_URL or "postgres" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"sslmode": "require"} if "supabase" in SQLALCHEMY_DATABASE_URL else {}
elif "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
print(SQLALCHEMY_DATABASE_URL)
inspector = inspect(engine)
metadata = MetaData()
metadata.reflect(bind=engine)
# Get all table names
table_names = inspector.get_table_names()

metadata.drop_all(engine)
# Print the table names
print("Tables in the database:")
for table_name in table_names:
    print(table_name)