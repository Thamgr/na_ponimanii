import logging
import httpx
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, API_HOST, API_PORT

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Define a function to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Привет, я твой бот!')

# Define a function to handle messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward the entire update to the FastAPI server."""
    # Convert the update to a dictionary
    update_dict = update.to_dict()
    
    # Send the update to the FastAPI server
    try:
        webhook_url = f"http://{API_HOST}:{API_PORT}/webhook"
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=update_dict)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Received response from server: {response_data}")
                # Note: We don't need to reply here as the server will send the response directly
            else:
                error_text = response.text
                logger.error(f"Error from server: {error_text}")
                await update.message.reply_text('Произошла ошибка при обработке сообщения.')
    except Exception as e:
        logger.error(f"Failed to send update to server: {e}")
        await update.message.reply_text('Не удалось связаться с сервером. Попробуйте позже.')

# Main function to run the bot
def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token from config.py
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
