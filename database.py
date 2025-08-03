from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL

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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model instance to a dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function should be called once at application startup.
    """
    Base.metadata.create_all(bind=engine)


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


def add_topic(user_id: int, title: str) -> Topic:
    """
    Add a new topic to the database.
    
    Args:
        user_id (int): ID of the user who created the topic
        title (str): Title of the topic
    
    Returns:
        Topic: The created topic
    """
    db = get_db()
    try:
        # Create a new Topic instance
        topic = Topic(user_id=user_id, title=title)
        
        # Add to the session and commit
        db.add(topic)
        db.commit()
        db.refresh(topic)
        
        return topic
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
    db = get_db()
    try:
        # Query topics for the user
        topics = db.query(Topic).filter(Topic.user_id == user_id).all()
        
        # Convert to dictionaries
        return [topic.to_dict() for topic in topics]
    finally:
        db.close()


# If this file is run directly, initialize the database
if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DATABASE_URL}")