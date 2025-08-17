import sys
import os
import sqlite3
import json
from datetime import datetime

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.config import DATABASE_URL

# Simple logging function
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def migrate_database():
    """
    Migrate the database to add the related_topics column to the topics table.
    """
    log("Starting database migration")
    
    # Extract the database path from the DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    log(f"Connecting to database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the related_topics column already exists
        cursor.execute("PRAGMA table_info(topics)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "related_topics" not in column_names:
            log("Adding related_topics column to topics table")
            
            # Add the related_topics column
            cursor.execute("ALTER TABLE topics ADD COLUMN related_topics TEXT")
            
            log("Column added successfully")
        else:
            log("related_topics column already exists")
            
        if "parent_topic_id" not in column_names:
            log("Adding parent_topic_id column to topics table")
            
            # Add the parent_topic_id column
            cursor.execute("ALTER TABLE topics ADD COLUMN parent_topic_id INTEGER")
            
            log("Column added successfully")
        else:
            log("parent_topic_id column already exists")
        
        # Commit the changes
        conn.commit()
        
        log("Database migration completed successfully")
    except Exception as e:
        log(f"Error migrating database: {str(e)} ({type(e).__name__})")
        raise
    finally:
        # Close the connection
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    log("Running database migration script")
    
    migrate_database()
    
    log("Database migration script completed")
    
    print("Database migration completed successfully")