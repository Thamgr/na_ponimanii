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

# Database Configuration
# Get database path from environment variable with fallback
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"
