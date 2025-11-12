"""
Configuración del sistema de logging
"""
import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from src.config import Config

def setup_logger(name):
    """
    Configura y devuelve un logger con nombre personalizado
    
    Args:
        name (str): Nombre del logger
        
    Returns:
        logging.Logger: Logger configurado
    """
    # Crear directorio de logs si no existe
    log_dir = Path(Config.LOG_FILE).parent
    if not log_dir.exists():
        os.makedirs(log_dir)
    
    # Configurar logger
    logger = logging.getLogger(name)
    
    # Evitar duplicación de handlers
    if not logger.handlers:
        logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Handler para archivo
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger