import logging
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from config import API_HOST, API_PORT, TOKEN

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

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting FastAPI server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
