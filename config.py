import os
import sys
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Link update configuration
UPDATE_INTERVAL_HOURS = 6

# MongoDB collections
COLLECTION_CHANNELS = "linked_channels"

# Setup logging configuration
def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file logger
    logger.add(
        "logs/bot.log",
        rotation="10 MB",
        retention="1 week",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    logger.info("Logging configured successfully")