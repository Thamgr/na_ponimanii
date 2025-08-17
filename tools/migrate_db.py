import sys
import os
import sqlite3
import json

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.config import DATABASE_URL
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("MIGRATION")

def migrate_database():
    """
    Migrate the database to add the related_topics column to the topics table.
    """
    logger.info(format_log_message(
        "Starting database migration"
    ))
    
    # Extract the database path from the DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    logger.info(format_log_message(
        "Connecting to database",
        db_path=db_path
    ))
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the related_topics column already exists
        cursor.execute("PRAGMA table_info(topics)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "related_topics" not in column_names:
            logger.info(format_log_message(
                "Adding related_topics column to topics table"
            ))
            
            # Add the related_topics column
            cursor.execute("ALTER TABLE topics ADD COLUMN related_topics TEXT")
            
            logger.info(format_log_message(
                "Column added successfully"
            ))
        else:
            logger.info(format_log_message(
                "related_topics column already exists"
            ))
        
        # Commit the changes
        conn.commit()
        
        logger.info(format_log_message(
            "Database migration completed successfully"
        ))
    except Exception as e:
        logger.error(format_log_message(
            "Error migrating database",
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        # Close the connection
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info(format_log_message(
        "Running database migration script"
    ))
    
    migrate_database()
    
    logger.info(format_log_message(
        "Database migration script completed"
    ))
    
    print("Database migration completed successfully")