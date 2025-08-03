import logging
import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from config import API_HOST, API_PORT, TOKEN
from database import init_db, add_topic, list_topics

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

@app.post("/topics", response_model=TopicResponse)
async def create_topic(topic: TopicCreate):
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
        
        # Convert to response model
        return TopicResponse(
            id=db_topic.id,
            user_id=db_topic.user_id,
            title=db_topic.title,
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

@app.post("/bot/add_topic", response_model=TopicResponse)
async def bot_add_topic(request: Request):
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
        
        # Add the topic to the database
        db_topic = add_topic(user_id, topic_title)
        
        # Return the topic data
        return TopicResponse(
            id=db_topic.id,
            user_id=db_topic.user_id,
            title=db_topic.title,
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
