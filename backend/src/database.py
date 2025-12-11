import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Try to read environment variables
# Note: The replace corrects a common SQLAlchemy error with Postgres URLs
DATABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    # --- CLOUD MODE (Android / Render) ---
    # If the URL starts with "postgres://", SQLAlchemy needs "postgresql://"
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    if "postgresql://" in DATABASE_URL and "pg8000" not in DATABASE_URL:
        # If it's for Android, it's better to ensure we use the correct driver
        # But to simplify, let's assume the connection string comes clean
        # and we'll add the driver if necessary, or trust that the environment has the driver.
        pass

    # IMPORTANT: For Android to work without psycopg2, the URL should be:
    # postgresql+pg8000://user:pass@host:port/db
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://")

    print(f"🔌 Connecting to Cloud: {DATABASE_URL.split('@')[1]}") # Safe print (hides the password)
    engine = create_engine(DATABASE_URL)

else:
    # --- LOCAL MODE ---
    print("📂 Using LOCAL database (SQLite)")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./tercasfc.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()