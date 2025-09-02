import httpx
import json
import sys
import os
import time

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from metrics.metrics import get_metrics_client
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from sqlalchemy import func

from env.config import API_HOST, API_PORT, DEFAULT_USER_MODE
from src.server.database import init_db, add_topic, list_topics, update_topic_explanation, update_db_metrics, get_random_topic_for_user, delete_topic, Topic, User, add_user, get_mode, toggle_mode
from src.server.llm_service import generate_explanation, generate_related_topics
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("SERVER")


# Create FastAPI application
app = FastAPI(
    title="Na Ponimanii API",
    description="API for Na Ponimanii Telegram Bot",
    version="0.1.0"
)

# Middleware to count requests
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    
    # Increment request counter
    get_metrics_client().incr(f'requests.{method}.{path}')
    
    # Call the next middleware or endpoint handler
    response = await call_next(request)
    
    # Track responses with status codes
    get_metrics_client().incr(f'responses.{response.status_code}.{method}.{path}')
    
    return response

# Initialize database on startup and set up metrics
@app.on_event("startup")
async def startup_event():
    """Initialize the database on application startup and set up metrics."""
    logger.info(format_log_message(
        "Initializing database"
    ))
    
    init_db()
    
    logger.info(format_log_message(
        "Database initialized successfully"
    ))
    
    # Start background task for periodic metrics updates
    asyncio.create_task(periodic_metrics_update())
    
async def periodic_metrics_update():
    """Periodically update metrics in the background."""
    logger.info(format_log_message(
        "Starting periodic metrics update task"
    ))
    
    while True:
        try:
            # Update metrics
            update_db_metrics()
            
            # Wait for 5 minutes before updating again
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(format_log_message(
                "Error in periodic metrics update task",
                error=str(e),
                error_type=type(e).__name__
            ))
            # Wait a bit before trying again
            await asyncio.sleep(60)


# Define request and response models
class TopicCreate(BaseModel):
    """Request model for creating a topic."""
    user_id: int
    title: str

class UserModeRequest(BaseModel):
    """Request model for user mode operations."""
    user_id: int

class UserModeResponse(BaseModel):
    """Response model for user mode operations."""
    user_id: int
    mode: str

class TopicResponse(BaseModel):
    """Response model for a topic."""
    id: int
    user_id: int
    title: str
    explanation: Optional[str] = None
    created_at: Optional[str] = None
    related_topics: Optional[List[str]] = None
    parent_topic_title: Optional[str] = None
    created_at: Optional[str] = None

class TopicListResponse(BaseModel):
    """Response model for a list of topics."""
    topics: List[TopicResponse]
        

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler to format error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "running"}

@app.post("/change_mode", response_model=UserModeResponse)
async def change_mode(request: Request):
    """
    Toggle the mode for a user between "short" and "long".
    
    Args:
        request: The request containing the user ID
        
    Returns:
        The user ID and new mode
    """
    logger.info(format_log_message(
        "Received change_mode request",
        client_host=request.client.host,
        method=request.method
    ))
    
    try:
        # Parse request body as JSON
        data = await request.json()
        # Validate required fields
        if 'user_id' not in data:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        user_id = data['user_id']
        
        # Toggle the user's mode
        new_mode = toggle_mode(user_id)
        
        # Return the user ID and new mode
        return {"user_id": user_id, "mode": new_mode}

    except Exception as e:
        logger.error(format_log_message(
            "Error processing change_mode request",
            error=str(e),
            error_type=type(e).__name__
        ))
        raise HTTPException(status_code=500, detail=str(e))

async def generate_and_save_explanation(topic_id: int, topic_title: str, parent_topic_title: Optional[str] = None, user_id: Optional[int] = None):
    """
    Background task to generate an explanation and related topics for a topic and save them to the database.
    
    Args:
        topic_id: The ID of the topic
        topic_title: The title of the topic
        parent_topic_title: The title of the parent topic, if available
        user_id: The ID of the user, used to determine the explanation mode
    """
    logger.info(format_log_message(
        "Starting background task to generate explanation and related topics",
        topic_id=topic_id,
        user_id=user_id
    ))
    
    try:
        # Get user's mode if user_id is provided
        mode = DEFAULT_USER_MODE
        if user_id is not None:
            mode = get_mode(user_id)
            logger.info(format_log_message(
                "Retrieved user mode for explanation",
                user_id=user_id,
                mode=mode
            ))
        
        # Generate explanation
        logger.info(format_log_message(
            "Requesting explanation from LLM service",
            topic_id=topic_id,
            mode=mode
        ))
        
        explanation = generate_explanation(topic_title, parent_topic_title, mode)

        logger.info(format_log_message(
            "Requesting related topics from LLM service with explanation context",
            topic_id=topic_id,
        ))
        
        related_topics = generate_related_topics(topic_title, explanation)
        updated_topic = update_topic_explanation(topic_id, explanation, related_topics)
        
        if not updated_topic:
            logger.error(format_log_message(
                "Failed to update topic with explanation and related topics",
                topic_id=topic_id,
            ))
        else:
            logger.info(format_log_message(
                "Successfully saved explanation and related topics to database",
                topic_id=topic_id
            ))
            

    except Exception as e:
        logger.error(format_log_message(
            "Unexpected error when generating explanation or related topics",
            topic_id=topic_id,
            error=str(e),
            error_type=type(e).__name__
        ))
 


@app.post("/bot/random_topic", response_model=Optional[TopicResponse])
async def bot_get_random_topic(request: Request):
    """
    Get a random topic for a user, explain it, and delete it.
    
    Args:
        request: The request containing the user ID
        
    Returns:
        The topic data with explanation, or None if no topics found
    """
    logger.info(format_log_message(
        "Received random_topic request",
        client_host=request.client.host,
        method=request.method
    ))
    
    try:
        # Parse request body as JSON
        data = await request.json()
        
        logger.debug(format_log_message(
            "Parsed random_topic request body",
            data=data
        ))
        
        # Validate required fields
        if 'user_id' not in data:
            logger.warning(format_log_message(
                "Missing user_id in random_topic request",
                data=data
            ))
            raise HTTPException(status_code=400, detail="user_id is required")
        
        user_id = data['user_id']
        
        # Ensure user exists in the database
        add_user(user_id)
        
        logger.info(format_log_message(
            "Getting random topic for user",
            user_id=user_id
        ))
        
        # Get a random topic for the user
        topic = get_random_topic_for_user(user_id)
        
        if not topic:
            logger.info(format_log_message(
                "No topics found for user",
                user_id=user_id
            ))
            return None
        
        logger.info(format_log_message(
            "Retrieved random topic",
            user_id=user_id,
            topic_id=topic.id,
            has_explanation=topic.explanation is not None
        ))
        
        # Generate explanation if not already present
        if not topic.explanation:
            time.sleep(3)
            logger.warning(format_log_message(
                "Explanation was not ready - wait another 3s",
                topic_id=topic.id
            ))
        
        # Get related topics from the database or generate them if not available
        related_topics = []
        if hasattr(topic, 'related_topics') and topic.related_topics:
            try:
                related_topics = json.loads(topic.related_topics)
                logger.info(format_log_message(
                    "Retrieved related topics from database",
                    topic_id=topic.id,
                    related_topics_count=len(related_topics)
                ))
            except Exception as e:
                logger.error(format_log_message(
                    "Error parsing related topics from database",
                    topic_id=topic.id,
                    error=str(e),
                    error_type=type(e).__name__
                ))
                # Continue even if parsing fails
        
        # If no related topics in the database, generate them on-the-fly
        if not related_topics:
            try:
                logger.info(format_log_message(
                    "Generating related topics on-the-fly with explanation context",
                    topic_id=topic.id,
                ))
                
                related_topics = generate_related_topics(topic.title, topic.explanation)
                
                # Note: We don't pass user_id here because the related topics format
                # doesn't change based on the user's mode preference
                
                logger.info(format_log_message(
                    "Received related topics from LLM service",
                    topic_id=topic.id,
                    related_topics_count=len(related_topics)
                ))
            except Exception as e:
                logger.error(format_log_message(
                    "Error generating related topics",
                    topic_id=topic.id,
                    error=str(e),
                    error_type=type(e).__name__
                ))
                # Continue even if related topics generation fails
        
        # Prepare response
        response = TopicResponse(
            id=topic.id,
            user_id=topic.user_id,
            title=topic.title,
            explanation=topic.explanation,
            created_at=topic.created_at.isoformat() if topic.created_at else None,
            related_topics=related_topics,
            parent_topic_title=topic.parent_topic_title
        )
        
        logger.info(format_log_message(
            "Random topic request completed successfully",
            user_id=user_id,
            topic_id=topic.id
        ))
        
        return response
    except Exception as e:
        logger.error(format_log_message(
            "Error processing random topic request",
            error=str(e),
            error_type=type(e).__name__
        ))
        raise HTTPException(status_code=500, detail="Failed to get random topic")


@app.post("/bot/add_topic", response_model=TopicResponse)
async def bot_add_topic(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint for the Telegram bot to add a topic.
    
    Args:
        request: The request containing the command data
        
    Returns:
        The added topic data or an error response
    """
    logger.info(format_log_message(
        "Received add_topic request",
        client_host=request.client.host,
        method=request.method
    ))
    
    try:
        # Parse request body as JSON
        data = await request.json()
        
        logger.debug(format_log_message(
            "Parsed add_topic request body",
            data=data
        ))
        
        # Validate required fields
        if 'user_id' not in data:
            logger.warning(format_log_message(
                "Missing user_id in add_topic request",
                data=data
            ))
            raise HTTPException(status_code=400, detail="user_id is required")
            
        if 'topic_title' not in data:
            logger.warning(format_log_message(
                "Missing topic_title in add_topic request",
                data=data
            ))
            raise HTTPException(status_code=400, detail="topic_title is required")
        
        user_id = data['user_id']
        topic_title = data['topic_title']
        parent_topic_title = data.get('parent_topic_title')  # Optional parent topic title
        
        # Ensure user exists in the database
        add_user(user_id)
        
        logger.info(format_log_message(
            "Processing add_topic request",
            user_id=user_id,
        ))
        
        # Check if topic title is empty
        if not topic_title.strip():
            logger.warning(format_log_message(
                "Empty topic_title provided",
                user_id=user_id
            ))
            # No topic provided
            raise HTTPException(status_code=400, detail="topic_title cannot be empty")
        
        # Add the topic to the database (without explanation initially)
        logger.info(format_log_message(
            "Adding topic to database",
            user_id=user_id,
        ))
        
        db_topic = add_topic(user_id, topic_title, parent_topic_title=parent_topic_title)
        
        background_tasks.add_task(
            generate_and_save_explanation,
            topic_id=db_topic.id,
            topic_title=topic_title,
            parent_topic_title=parent_topic_title,
            user_id=user_id
        )
        
        # Return the topic data
        response = TopicResponse(
            id=db_topic.id,
            user_id=db_topic.user_id,
            title=db_topic.title,
            explanation=None,  # Explanation will be added later
            parent_topic_title=db_topic.parent_topic_title,
            created_at=db_topic.created_at.isoformat() if db_topic.created_at else None
        )
        
        logger.info(format_log_message(
            "Add_topic request completed successfully",
            user_id=user_id,
            topic_id=db_topic.id
        ))
        
        return response
    
    except ValueError:
        # Handle invalid JSON
        logger.error(format_log_message(
            "Received invalid JSON in add_topic request",
            client_host=request.client.host
        ))
        raise HTTPException(status_code=400, detail="invalid json")
    except Exception as e:
        logger.error(format_log_message(
            "Error processing add_topic request",
            error=str(e),
            error_type=type(e).__name__
        ))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/list_topics", response_model=TopicListResponse)
async def bot_list_topics(request: Request):
    """
    Endpoint for the Telegram bot to list topics.
    
    Args:
        request: The request containing the command data
        
    Returns:
        A list of topics for the user
    """
    logger.info(format_log_message(
        "Received list_topics request",
        client_host=request.client.host,
        method=request.method
    ))
    
    try:
        # Parse request body as JSON
        data = await request.json()
        
        logger.debug(format_log_message(
            "Parsed list_topics request body",
        ))
        
        # Validate required fields
        if 'user_id' not in data:
            logger.warning(format_log_message(
                "Missing user_id in list_topics request",
                data=data
            ))
            raise HTTPException(status_code=400, detail="user_id is required")
        
        user_id = data['user_id']
        
        # Ensure user exists in the database
        add_user(user_id)
        
        logger.info(format_log_message(
            "Retrieving topics for user",
            user_id=user_id
        ))
        
        # Get topics from the database
        topics = list_topics(user_id)
        
        logger.info(format_log_message(
            "Retrieved topics from database",
            user_id=user_id,
            topic_count=len(topics)
        ))
        
        # Return the topics list
        response = TopicListResponse(topics=topics)
        
        logger.info(format_log_message(
            "List_topics request completed successfully",
            user_id=user_id,
            topic_count=len(topics)
        ))
        
        return response
    
    except ValueError:
        # Handle invalid JSON
        logger.error(format_log_message(
            "Received invalid JSON in list_topics request",
            client_host=request.client.host
        ))
        raise HTTPException(status_code=400, detail="invalid json")
    except Exception as e:
        logger.error(format_log_message(
            "Error processing list_topics request",
            error=str(e),
            error_type=type(e).__name__
        ))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/delete_topic")
async def bot_delete_topic(request: Request):
    """
    Endpoint for the Telegram bot to delete a topic.
    
    Args:
        request: The request containing the topic ID
        
    Returns:
        A success message or an error response
    """
    logger.info(format_log_message(
        "Received delete_topic request",
        client_host=request.client.host,
        method=request.method
    ))
    
    try:
        # Parse request body as JSON
        data = await request.json()
        
        logger.debug(format_log_message(
            "Parsed delete_topic request body",
            data=data
        ))
        
        # Validate required fields
        if 'topic_id' not in data:
            logger.warning(format_log_message(
                "Missing topic_id in delete_topic request",
                data=data
            ))
            raise HTTPException(status_code=400, detail="topic_id is required")
        
        topic_id = data['topic_id']
        
        # Delete the topic
        success = delete_topic(topic_id)
        
        if not success:
            logger.warning(format_log_message(
                "Topic not found or could not be deleted",
                topic_id=topic_id
            ))
            raise HTTPException(status_code=404, detail="Topic not found or could not be deleted")
        
        logger.info(format_log_message(
            "Delete_topic request completed successfully",
            topic_id=topic_id
        ))
        
        return {"status": "success", "message": "Topic deleted successfully"}

    except Exception as e:
        logger.error(format_log_message(
            "Error processing delete_topic request",
            error=str(e),
            error_type=type(e).__name__
        ))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting FastAPI server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
