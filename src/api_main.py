from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
from src.config import Config
from src.api.routes import router as facturas_router
from src.database.database import engine, Base
from src.database import models 
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación
    - Crea las tablas de la base de datos al iniciar
    """
    # Crear tablas
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas de base de datos creadas/verificadas")
    except Exception as e:
        logger.error(f"Error al crear tablas: {str(e)}")
    
    yield
    
    # Cleanup si es necesario
    logger.info("Cerrando aplicación")


app = FastAPI(
    title="API de Facturación Electrónica AFIP",
    description="API REST para generar facturas electrónicas a través del WebService SOAP de AFIP/ARCA",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(facturas_router)


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "service": "Facturación API",
        "status": "online",
        "mode": "TESTING" if Config.AFIP_CONFIG["testing"] else "PRODUCTION",
        "message": "API de Facturación Electrónica AFIP",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "facturas": "/api/facturas"
        }
    }


@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {"status": "ok", "service": "facturacion"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones"""
    logger.error(f"Error no manejado: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.api_main:app",
        host="0.0.0.0",
        port=8001,  # Puerto diferente al backend principal
        reload=True
    )