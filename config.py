# Configuration
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
# Get token from environment variable with fallback to default value
TOKEN = os.getenv("TELEGRAM_TOKEN", "LOL")

# FastAPI Configuration
# Get host and port from environment variables with fallbacks
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
