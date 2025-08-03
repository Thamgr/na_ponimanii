import logging
import httpx
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from config import API_HOST, API_PORT, TOKEN
from database import init_db, add_topic, list_topics, update_topic_explanation, get_topic, get_random_topic_for_user, delete_topic
from llm_service import generate_explanation, generate_related_topics, LLMServiceException

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Na Ponimanii API",
    description="API for Na Ponimanii Telegram Bot",
    version="0.1.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the database on application startup."""
    init_db()
    logger.info("Database initialized")

# Define request and response models
class TopicCreate(BaseModel):
    """Request model for creating a topic."""
    user_id: int
    title: str
class TopicResponse(BaseModel):
    """Response model for a topic."""
    id: int
    user_id: int
    title: str
    explanation: Optional[str] = None
    created_at: Optional[str] = None
    related_topics: Optional[List[str]] = None
    created_at: Optional[str] = None

class TopicListResponse(BaseModel):
    """Response model for a list of topics."""
    topics: List[TopicResponse]

@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint to receive Telegram updates from the bot.
    
    Extracts the message text and sends a response back to the user
    via the Telegram Bot API.
    """
    try:
        # Parse request body as JSON (this should be the Telegram update)
        update = await request.json()
        
        # Validate if update contains a message
        if 'message' not in update:
            logger.warning("Received webhook request without 'message' field")
            raise HTTPException(status_code=400, detail="no message")
        
        # Extract message details
        message = update['message']
        if 'text' not in message:
            logger.warning("Received message without 'text' field")
            raise HTTPException(status_code=400, detail="no text in message")
        
        chat_id = message['chat']['id']
        message_text = message['text']
        
        # Log the received message
        logger.info(f"Received message from chat {chat_id}: {message_text}")
        
        # Send response back to the user via Telegram Bot API
        response_text = f"Получено: {message_text}"
        await send_telegram_message(chat_id, response_text)
        
        # Return success response
        # Check if this is a command that should be handled by the bot
        if message_text.startswith('/'):
            return {"status": "ok", "command": True}
            
        return {"status": "ok"}
    
    except ValueError:
        # Handle invalid JSON
        logger.error("Received invalid JSON in webhook request")
        raise HTTPException(status_code=400, detail="invalid json")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler to format error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

async def send_telegram_message(chat_id: int, text: str):
    """
    Send a message to a Telegram chat using the Telegram Bot API.
    
    Args:
        chat_id: The ID of the chat to send the message to
        text: The text of the message to send
    """
    telegram_api_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # Prepare the request data
    data = {
        "chat_id": chat_id,
        "text": text
    }
    
    # Send the request to the Telegram Bot API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(telegram_api_url, json=data)
            response_data = response.json()
            
            if not response.is_success or not response_data.get('ok'):
                logger.error(f"Failed to send message to Telegram: {response_data}")
                return False
            
            logger.info(f"Successfully sent message to chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "running"}

async def generate_and_save_explanation(topic_id: int, topic_title: str):
    """
    Background task to generate an explanation for a topic and save it to the database.
    
    Args:
        topic_id: The ID of the topic
        topic_title: The title of the topic
    """
    try:
        # Generate explanation
        logger.info(f"Generating explanation for topic: {topic_title}")
        explanation = generate_explanation(topic_title)
        
        # Save explanation to database
        logger.info(f"Saving explanation for topic ID: {topic_id}")
        updated_topic = update_topic_explanation(topic_id, explanation)
        
        if not updated_topic:
            logger.error(f"Failed to update topic with ID: {topic_id}")
    except LLMServiceException as e:
        logger.error(f"LLM service error for topic '{topic_title}': {e}")
    except Exception as e:
        logger.error(f"Error generating explanation for topic '{topic_title}': {e}")

@app.post("/topics", response_model=TopicResponse)
async def create_topic(topic: TopicCreate, background_tasks: BackgroundTasks):
    """
    Create a new topic.
    
    Args:
        topic: The topic to create
        
    Returns:
        The created topic
    """
    try:
        # Add the topic to the database
        db_topic = add_topic(topic.user_id, topic.title)
        
        # Schedule background task to generate and save explanation
        background_tasks.add_task(
            generate_and_save_explanation,
            topic_id=db_topic.id,
            topic_title=topic.title
        )
        
        # Convert to response model
        return TopicResponse(
            id=db_topic.id,
            user_id=db_topic.user_id,
            title=db_topic.title,
            explanation=None,  # Explanation will be added later
            created_at=db_topic.created_at.isoformat() if db_topic.created_at else None
        )
    except Exception as e:
        logger.error(f"Error adding topic: {e}")
        raise HTTPException(status_code=500, detail="Failed to add topic")

@app.get("/topics/{user_id}", response_model=TopicListResponse)
async def get_topics(user_id: int):
    """
    Get all topics for a user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        A list of topics
    """
    try:
        # Get topics from the database
        topics = list_topics(user_id)
        
        # Convert to response model
        return TopicListResponse(topics=topics)
    except Exception as e:
        logger.error(f"Error listing topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to list topics")

@app.post("/bot/random_topic", response_model=Optional[TopicResponse])
async def bot_get_random_topic(request: Request):
    """
    Get a random topic for a user, explain it, and delete it.
    
    Args:
        request: The request containing the user ID
        
    Returns:
        The topic data with explanation, or None if no topics found
    """
    try:
        # Parse request body as JSON
        data = await request.json()
        
        # Validate required fields
        if 'user_id' not in data:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        user_id = data['user_id']
        
        # Get a random topic for the user
        topic = get_random_topic_for_user(user_id)
        
        if not topic:
            return None
        
        # Generate explanation if not already present
        if not topic.explanation:
            try:
                logger.info(f"Generating explanation for topic: {topic.title}")
                explanation = generate_explanation(topic.title)
                topic = update_topic_explanation(topic.id, explanation)
            except Exception as e:
                logger.error(f"Error generating explanation: {e}")
                # Continue even if explanation generation fails
        
        # Generate related topics
        related_topics = []
        try:
            logger.info(f"Generating related topics for: {topic.title}")
            related_topics = generate_related_topics(topic.title)
        except Exception as e:
            logger.error(f"Error generating related topics: {e}")
            # Continue even if related topics generation fails
        
        # Prepare response
        response = TopicResponse(
            id=topic.id,
            user_id=topic.user_id,
            title=topic.title,
            explanation=topic.explanation,
            created_at=topic.created_at.isoformat() if topic.created_at else None,
            related_topics=related_topics
        )
        
        # Delete the topic
        delete_topic(topic.id)
        
        return response
    except Exception as e:
        logger.error(f"Error getting random topic: {e}")
        raise HTTPException(status_code=500, detail="Failed to get random topic")

@app.get("/bot/topic/{topic_id}", response_model=TopicResponse)
async def bot_get_topic(topic_id: int):
    """
    Get a specific topic by ID.
    
    Args:
        topic_id: The ID of the topic to retrieve
        
    Returns:
        The topic data
    """
    try:
        # Get the topic from the database
        topic = get_topic(topic_id)
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Return the topic data
        return TopicResponse(
            id=topic.id,
            user_id=topic.user_id,
            title=topic.title,
            explanation=topic.explanation,
            created_at=topic.created_at.isoformat() if topic.created_at else None
        )
    except Exception as e:
        logger.error(f"Error getting topic: {e}")
        raise HTTPException(status_code=500, detail="Failed to get topic")

@app.post("/bot/add_topic", response_model=TopicResponse)
async def bot_add_topic(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint for the Telegram bot to add a topic.
    
    Args:
        request: The request containing the command data
        
    Returns:
        The added topic data or an error response
    """
    try:
        # Parse request body as JSON
        data = await request.json()
        
        # Validate required fields
        if 'user_id' not in data:
            raise HTTPException(status_code=400, detail="user_id is required")
        if 'topic_title' not in data:
            raise HTTPException(status_code=400, detail="topic_title is required")
        
        user_id = data['user_id']
        topic_title = data['topic_title']
        
        # Check if topic title is empty
        if not topic_title.strip():
            # No topic provided
            raise HTTPException(status_code=400, detail="topic_title cannot be empty")
        
        # Add the topic to the database (without explanation initially)
        db_topic = add_topic(user_id, topic_title)
        
        # Schedule background task to generate and save explanation
        background_tasks.add_task(
            generate_and_save_explanation,
            topic_id=db_topic.id,
            topic_title=topic_title
        )
        
        # Return the topic data
        return TopicResponse(
            id=db_topic.id,
            user_id=db_topic.user_id,
            title=db_topic.title,
            explanation=None,  # Explanation will be added later
            created_at=db_topic.created_at.isoformat() if db_topic.created_at else None
        )
    
    except ValueError:
        # Handle invalid JSON
        logger.error("Received invalid JSON in add_topic request")
        raise HTTPException(status_code=400, detail="invalid json")
    except Exception as e:
        logger.error(f"Error adding topic: {e}")
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
    try:
        # Parse request body as JSON
        data = await request.json()
        
        # Validate required fields
        if 'user_id' not in data:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        user_id = data['user_id']
        
        # Get topics from the database
        topics = list_topics(user_id)
        
        # Return the topics list
        return TopicListResponse(topics=topics)
    
    except ValueError:
        # Handle invalid JSON
        logger.error("Received invalid JSON in list_topics request")
        raise HTTPException(status_code=400, detail="invalid json")
    except Exception as e:
        logger.error(f"Error listing topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting FastAPI server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
