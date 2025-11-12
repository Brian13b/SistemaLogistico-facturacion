"""
Configuración de base de datos para el módulo de facturación
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# URL de la base de datos (usando PostgreSQL)
# Base de datos separada para facturación
DATABASE_URL = os.getenv(
    "DATABASE_URL_FACTURACION",
    "postgresql://user:password@localhost:5432/facturacion"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency para obtener una sesión de base de datos
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

