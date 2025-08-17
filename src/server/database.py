from datetime import datetime
import random
import sys
import os
import json
from typing import List, Dict, Any, Optional

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from env.config import DATABASE_URL
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("DB")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


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
    related_topics = Column(Text, nullable=True)  # New column for storing related topics as JSON
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


def add_topic(user_id: int, title: str, explanation: Optional[str] = None) -> Topic:
    """
    Add a new topic to the database.
    
    Args:
        user_id (int): ID of the user who created the topic
        title (str): Title of the topic
        explanation (Optional[str]): Explanation of the topic, if available
    
    Returns:
        Topic: The created topic
    """
    logger.info(format_log_message(
        "Adding topic to database",
        user_id=user_id,
        title=title,
        has_explanation=explanation is not None
    ))
    
    db = get_db()
    try:
        # Create a new Topic instance
        topic = Topic(user_id=user_id, title=title, explanation=explanation)
        
        # Add to the session and commit
        db.add(topic)
        db.commit()
        db.refresh(topic)
        
        logger.info(format_log_message(
            "Topic added successfully",
            user_id=user_id,
            topic_id=topic.id,
            title=topic.title
        ))
        
        return topic
    except Exception as e:
        logger.error(format_log_message(
            "Error adding topic to database",
            user_id=user_id,
            title=title,
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
                topic_title=topic.title,
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
            title=title
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
                title=topic.title
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
                title=topic.title,
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