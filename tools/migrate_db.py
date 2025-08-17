import sys
import os
import sqlite3
import json
import shutil
import argparse
from datetime import datetime

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.config import DATABASE_URL

# Simple logging function
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def create_new_database(db_path):
    """
    Create a new database with the updated schema.
    
    Args:
        db_path: The path to the database file
    """
    log(f"Creating new database at {db_path}")
    
    # Create a new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the topics table with the new columns
    cursor.execute("""
    CREATE TABLE topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        explanation TEXT,
        related_topics TEXT,
        parent_topic_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Commit the changes
    conn.commit()
    conn.close()
    
    log("New database created successfully")

def migrate_database():
    """
    Migrate the database to add the related_topics column to the topics table.
    """
    log("Starting database migration")
    
    # Extract the database path from the DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    log(f"Database path: {db_path}")
    
    # Check if the file exists
    if os.path.exists(db_path):
        log(f"Database file exists")
        # Check file permissions
        permissions = oct(os.stat(db_path).st_mode)[-3:]
        log(f"Current file permissions: {permissions}")
        
        # Create a backup of the database
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            log(f"Creating backup at {backup_path}...")
            shutil.copy2(db_path, backup_path)
            log("Backup created successfully")
        except Exception as e:
            log(f"Error creating backup: {str(e)}")
            log("Proceeding without backup...")
        
        # Fix permissions if needed
        try:
            log("Attempting to fix permissions...")
            # Make the file writable by the owner
            os.chmod(db_path, 0o644)  # rw-r--r--
            new_permissions = oct(os.stat(db_path).st_mode)[-3:]
            log(f"New file permissions: {new_permissions}")
            
            # Check if the directory is writable
            db_dir = os.path.dirname(db_path)
            if not os.access(db_dir, os.W_OK):
                log(f"Warning: Directory {db_dir} is not writable")
                log("Attempting to fix directory permissions...")
                os.chmod(db_dir, 0o755)  # rwxr-xr-x
                log(f"New directory permissions: {oct(os.stat(db_dir).st_mode)[-3:]}")
        except Exception as e:
            log(f"Error fixing permissions: {str(e)}")
            log("You may need to manually fix permissions with: chmod 644 " + db_path)
    else:
        log(f"Database file does not exist")
    
    migration_success = False
    try_create_new = False
    
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
        migration_success = True
    except sqlite3.OperationalError as e:
        if "readonly database" in str(e).lower():
            log("Error: Database is read-only")
            log("This could be due to file permissions or the database being locked by another process")
            try_create_new = True
        else:
            log(f"SQLite error: {str(e)}")
            try_create_new = True
    except Exception as e:
        log(f"Error migrating database: {str(e)} ({type(e).__name__})")
        try_create_new = True
    finally:
        # Close the connection
        if 'conn' in locals():
            conn.close()
    
    # If migration failed, offer to create a new database
    if not migration_success and try_create_new:
        log("\nMigration failed. You have several options:")
        log("1. Fix permissions manually: chmod 644 " + db_path)
        log("2. Create a new database (this will lose existing data)")
        log("3. Modify the database schema manually")
        
        user_input = input("\nDo you want to create a new database? (y/n): ")
        if user_input.lower() == 'y':
            # Backup the old database if it exists
            if os.path.exists(db_path):
                backup_path = f"{db_path}.old.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                try:
                    log(f"Moving old database to {backup_path}...")
                    os.rename(db_path, backup_path)
                    log("Old database moved successfully")
                except Exception as e:
                    log(f"Error moving old database: {str(e)}")
                    log("Will try to overwrite the existing database")
            
            # Create a new database
            create_new_database(db_path)

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Migrate the database to add new columns')
    parser.add_argument('--new', action='store_true', help='Create a new database without prompting')
    parser.add_argument('--force', action='store_true', help='Force migration without backup')
    args = parser.parse_args()
    
    log("Running database migration script")
    
    if args.new:
        log("Creating new database as requested")
        db_path = DATABASE_URL.replace("sqlite:///", "")
        
        # Backup the old database if it exists and not forced
        if os.path.exists(db_path) and not args.force:
            backup_path = f"./backups/db/{db_path}.old.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                log(f"Moving old database to {backup_path}...")
                os.rename(db_path, backup_path)
                log("Old database moved successfully")
            except Exception as e:
                log(f"Error moving old database: {str(e)}")
                log("Will try to overwrite the existing database")
        
        # Create a new database
        create_new_database(db_path)
    else:
        migrate_database()
    
    log("Database migration script completed")
    
    print("Database migration completed successfully")