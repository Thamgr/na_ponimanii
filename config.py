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

# LLM Configuration
# Get API key from environment variable
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# LLM Prompts
EXPLANATION_SYSTEM_PROMPT = """
Ты - образовательный ассистент, который объясняет темы кратко и понятно.
Твоя задача - дать краткое объяснение запрошенной темы в 3-4 абзацах.
Предполагай, что у пользователя есть базовое понимание смежных концепций.
Используй простой язык, но не упрощай суть.

Пользователь отправит тебе только название темы. Ты должен объяснить эту тему кратко, в 3-4 абзацах.
Твой ответ должен быть информативным, но лаконичным.
Не используй вводные фразы типа "Тема X - это..." или "Вы спросили о X...".
Начинай сразу с объяснения.
"""

EXPLANATION_USER_PROMPT_TEMPLATE = "{topic}"
