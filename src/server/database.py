from datetime import datetime
import random
import sys
import os
import json
from typing import List, Dict, Any, Optional

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from metrics.metrics import get_metrics_client

from env.config import DATABASE_URL
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("DB")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

# Create Base class
Base = declarative_base()


class User(Base):
    """
    SQLAlchemy model for the users table.
    
    Columns:
        user_id (int): Primary key, ID of the user
        mode (str): User's preference mode ("short" or "long")
    """
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    mode = Column(String, default="long")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model instance to a dictionary."""
        return {
            "user_id": self.user_id,
            "mode": self.mode
        }


class Topic(Base):
    """
    SQLAlchemy model for the topics table.
    
    Columns:
        id (int): Primary key, auto-generated
        user_id (int): ID of the user who created the topic
        title (str): Title of the topic
        created_at (datetime): Timestamp when the topic was created
    """
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    title = Column(String, index=True)
    explanation = Column(Text, nullable=True)  # Column for storing explanations
    related_topics = Column(Text, nullable=True)  # Column for storing related topics as JSON
    parent_topic_title = Column(String, nullable=True)  # Column for storing parent topic title
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model instance to a dictionary."""
        related_topics_list = json.loads(self.related_topics) if self.related_topics else []
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "explanation": self.explanation,
            "related_topics": related_topics_list,
            "parent_topic_title": self.parent_topic_title,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function should be called once at application startup.
    """
    logger.info(format_log_message(
        "Initializing database",
        database_url=DATABASE_URL
    ))
    
    Base.metadata.create_all(bind=engine)
    
    logger.info(format_log_message(
        "Database initialized successfully"
    ))


def get_db() -> Session:
    """
    Get a database session.
    
    Returns:
        Session: A SQLAlchemy session
    
    Usage:
        db = get_db()
        try:
            # Use the session
            ...
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def add_topic(user_id: int, title: str, explanation: Optional[str] = None, parent_topic_title: Optional[str] = None) -> Topic:
    """
    Add a new topic to the database.
    
    Args:
        user_id (int): ID of the user who created the topic
        title (str): Title of the topic
        explanation (Optional[str]): Explanation of the topic, if available
        parent_topic_title (Optional[str]): Title of the parent topic, if available
    
    Returns:
        Topic: The created topic
    """
    logger.info(format_log_message(
        "Adding topic to database",
        user_id=user_id,
        has_explanation=explanation is not None,
    ))
    
    db = get_db()
    try:
        # Create a new Topic instance
        topic = Topic(user_id=user_id, title=title, explanation=explanation, parent_topic_title=parent_topic_title)
        
        # Add to the session and commit
        db.add(topic)
        db.commit()
        db.refresh(topic)
        
        logger.info(format_log_message(
            "Topic added successfully",
            user_id=user_id,
            topic_id=topic.id,
        ))
        
        return topic
    except Exception as e:
        logger.error(format_log_message(
            "Error adding topic to database",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        db.close()


def get_random_topic_for_user(user_id: int) -> Optional[Topic]:
    """
    Get a random topic for a specific user.
    
    Args:
        user_id (int): ID of the user
    
    Returns:
        Optional[Topic]: A random topic, or None if no topics found
    """
    logger.info(format_log_message(
        "Getting random topic for user",
        user_id=user_id
    ))
    
    db = get_db()
    try:
        # Count topics for the user
        topic_count = db.query(Topic).filter(Topic.user_id == user_id).count()
        
        if topic_count == 0:
            logger.info(format_log_message(
                "No topics found for user",
                user_id=user_id
            ))
            return None
        
        # Get a random offset
        random_offset = random.randint(0, topic_count - 1)
        
        logger.debug(format_log_message(
            "Selected random topic offset",
            user_id=user_id,
            topic_count=topic_count,
            random_offset=random_offset
        ))
        
        # Get a random topic
        topic = db.query(Topic).filter(Topic.user_id == user_id).offset(random_offset).first()
        
        if topic:
            logger.info(format_log_message(
                "Retrieved random topic",
                user_id=user_id,
                topic_id=topic.id,
                has_explanation=topic.explanation is not None
            ))
        
        return topic
    except Exception as e:
        logger.error(format_log_message(
            "Error getting random topic for user",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        db.close()

def delete_topic(topic_id: int) -> bool:
    """
    Delete a topic from the database.
    
    Args:
        topic_id (int): ID of the topic to delete
    
    Returns:
        bool: True if the topic was deleted, False otherwise
    """
    logger.info(format_log_message(
        "Deleting topic",
        topic_id=topic_id
    ))
    
    db = get_db()
    try:
        # Find the topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        
        if not topic:
            logger.warning(format_log_message(
                "Topic not found for deletion",
                topic_id=topic_id
            ))
            return False
        
        user_id = topic.user_id
        title = topic.title
        
        # Delete the topic
        db.delete(topic)
        db.commit()
        
        logger.info(format_log_message(
            "Topic deleted successfully",
            topic_id=topic_id,
            user_id=user_id,
        ))
        
        return True
    except Exception as e:
        logger.error(format_log_message(
            "Error deleting topic",
            topic_id=topic_id,
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        db.close()

def update_topic_explanation(topic_id: int, explanation: str, related_topics: Optional[List[str]] = None) -> Optional[Topic]:
    """
    Update the explanation and related topics for an existing topic.
    
    Args:
        topic_id (int): ID of the topic to update
        explanation (str): New explanation for the topic
        related_topics (Optional[List[str]]): List of related topics
    
    Returns:
        Optional[Topic]: The updated topic, or None if not found
    """
    logger.info(format_log_message(
        "Updating topic explanation and related topics",
        topic_id=topic_id,
        explanation_length=len(explanation) if explanation else 0,
        related_topics_count=len(related_topics) if related_topics else 0
    ))
    
    db = get_db()
    try:
        # Find the topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        
        if topic:
            # Update the explanation
            topic.explanation = explanation
            
            # Update related topics if provided
            if related_topics is not None:
                topic.related_topics = json.dumps(related_topics)
                
            db.commit()
            db.refresh(topic)
            
            logger.info(format_log_message(
                "Topic explanation and related topics updated successfully",
                topic_id=topic_id,
                user_id=topic.user_id,
            ))
        else:
            logger.warning(format_log_message(
                "Topic not found for explanation update",
                topic_id=topic_id
            ))
            
        return topic
    except Exception as e:
        logger.error(format_log_message(
            "Error updating topic explanation and related topics",
            topic_id=topic_id,
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        db.close()

def get_topic(topic_id: int) -> Optional[Topic]:
    """
    Get a topic by ID.
    
    Args:
        topic_id (int): ID of the topic to retrieve
    
    Returns:
        Optional[Topic]: The topic, or None if not found
    """
    logger.info(format_log_message(
        "Getting topic by ID",
        topic_id=topic_id
    ))
    
    db = get_db()
    try:
        # Find the topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        
        if topic:
            logger.info(format_log_message(
                "Retrieved topic",
                topic_id=topic_id,
                user_id=topic.user_id,
                has_explanation=topic.explanation is not None
            ))
        else:
            logger.warning(format_log_message(
                "Topic not found",
                topic_id=topic_id
            ))
            
        return topic
    except Exception as e:
        logger.error(format_log_message(
            "Error getting topic",
            topic_id=topic_id,
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        db.close()

def list_topics(user_id: int) -> List[Dict[str, Any]]:
    """
    List all topics for a specific user.
    
    Args:
        user_id (int): ID of the user
    
    Returns:
        List[Dict[str, Any]]: List of topics as dictionaries
    """
    logger.info(format_log_message(
        "Listing topics for user",
        user_id=user_id
    ))
    
    db = get_db()
    try:
        # Query topics for the user
        topics = db.query(Topic).filter(Topic.user_id == user_id).all()
        
        logger.info(format_log_message(
            "Retrieved topics for user",
            user_id=user_id,
            topic_count=len(topics)
        ))
        
        # Convert to dictionaries
        result = [topic.to_dict() for topic in topics]
        
        return result
    except Exception as e:
        logger.error(format_log_message(
            "Error listing topics for user",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        db.close()


def add_user(user_id: int, mode: str = "long") -> User:
    """
    Add a new user to the database or update existing user's mode.
    
    Args:
        user_id (int): ID of the user
        mode (str): User's preference mode ("short" or "long"), defaults to "long"
    
    Returns:
        User: The created or updated user
    """
    logger.info(format_log_message(
        "Adding or updating user in database",
        user_id=user_id,
        mode=mode
    ))
    
    db = get_db()
    try:
        # Check if user already exists
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if user:
            # Update existing user
            user.mode = mode
            logger.info(format_log_message(
                "Updating existing user",
                user_id=user_id,
                mode=mode
            ))
        else:
            # Create a new User instance
            user = User(user_id=user_id, mode=mode)
            db.add(user)
            logger.info(format_log_message(
                "Creating new user",
                user_id=user_id,
                mode=mode
            ))
        
        # Commit changes
        db.commit()
        db.refresh(user)
        
        logger.info(format_log_message(
            "User added/updated successfully",
            user_id=user_id,
            mode=user.mode
        ))
        
        return user
    except Exception as e:
        logger.error(format_log_message(
            "Error adding/updating user in database",
            user_id=user_id,
            mode=mode,
            error=str(e),
            error_type=type(e).__name__
        ))
        raise
    finally:
        db.close()

def get_mode(user_id: int) -> str:
    """
    Get the mode for a specific user.
    
    Args:
        user_id (int): ID of the user
    
    Returns:
        str: The user's mode ("short" or "long"), defaults to "long" if user not found
    """
    
    db = get_db()
    try:
        # Find the user
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if user:
            return user.mode
        else:
            return "long"
    except Exception as e:
        logger.error(format_log_message(
            "Error getting user mode",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        ))
        # Return default mode in case of error
        return "long"
    finally:
        db.close()

def toggle_mode(user_id: int) -> str:
    """
    Toggle the mode for a specific user between "short" and "long".
    
    Args:
        user_id (int): ID of the user
    
    Returns:
        str: The new mode after toggling
    """
    # Get current mode
    current_mode = get_mode(user_id)
    
    # Toggle mode
    new_mode = "short" if current_mode == "long" else "long"
    
    # Update user with new mode
    add_user(user_id, new_mode)
    
    return new_mode


def update_db_metrics():
    """Update application metrics including unique user count and users table count."""
    try:
        # Get a database session
        db = get_db()
        
        # Count rows in the topics table
        topics_row_count = db.query(func.count(Topic.user_id)).scalar()
        
        # Count unique user_ids in the topics table
        active_users_count = db.query(func.count(func.distinct(Topic.user_id))).scalar()
        
        # Count records in the users table
        users_unique_count = db.query(func.count(User.user_id)).scalar()
        
        # Send the metrics to StatsD
        get_metrics_client().gauge('users.active_count', active_users_count)
        get_metrics_client().gauge('users.unique_count', users_unique_count)
        get_metrics_client().gauge('topics.count', topics_row_count)
    except Exception as e:
        logger.error(format_log_message(
            "Error updating metrics",
            error=str(e),
            error_type=type(e).__name__
        ))
    finally:
        if 'db' in locals():
            db.close()


# If this file is run directly, initialize the database
if __name__ == "__main__":
    logger.info(format_log_message(
        "Running database initialization script"
    ))
    
    init_db()
    
    logger.info(format_log_message(
        "Database initialization script completed",
        database_url=DATABASE_URL
    ))
    
    print(f"Database initialized at {DATABASE_URL}")