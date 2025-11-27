from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# We will use SQLite for now. It creates a file named tercasfc.db

SQLALCHEMY_DATABASE_URL = "sqlite:///.tercasfc.db"

# Create the engine that comunicates with the database
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create a sessionlocal class. Each instance is a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models to inherit from
Base = declarative_base()