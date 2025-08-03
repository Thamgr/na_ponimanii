import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from config import API_HOST, API_PORT

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
    Endpoint to receive messages from Telegram bot.
    
    Validates if the request body contains a 'message' field.
    Returns 200 OK with {"status":"ok"} if successful.
    Returns 400 with {"error":"no message"} if validation fails.
    """
    try:
        # Parse request body as JSON
        data = await request.json()
        
        # Validate if 'message' field exists
        if 'message' not in data:
            logger.warning("Received webhook request without 'message' field")
            raise HTTPException(status_code=400, detail="no message")
        
        # Log the received message
        logger.info(f"Received message: {data['message']}")
        
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

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting FastAPI server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
