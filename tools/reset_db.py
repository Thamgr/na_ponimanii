#!/usr/bin/env python3
"""
Script to reset the database by deleting the database file and recreating it.
"""

import os
import sys
import logging

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.config import DB_PATH
from src.server.database import init_db

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def reset_database():
    """Delete the database file and recreate it."""
    try:
        # Check if the database file exists
        if os.path.exists(DB_PATH):
            # Delete the database file
            os.remove(DB_PATH)
            logger.info(f"Deleted database file: {DB_PATH}")
        else:
            logger.info(f"Database file does not exist: {DB_PATH}")
        
        # Initialize the database
        init_db()
        logger.info(f"Initialized new database: {DB_PATH}")
        
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database reset...")
    success = reset_database()
    
    if success:
        logger.info("Database reset completed successfully.")
    else:
        logger.error("Database reset failed.")