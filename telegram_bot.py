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
    await update.message.reply_text('Привет, я твой бот! Используй /add <тема> чтобы добавить новую тему для изучения. Используй /list чтобы увидеть свои темы. Используй /topic чтобы получить объяснение случайной темы.')

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

# Define a function to handle the /add command
async def add_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /add command to add a new topic."""
    # Get the user ID
    user_id = update.effective_user.id
    
    # Get the command text
    message_text = update.message.text
    
    # Extract the topic title (everything after /add)
    topic_title = ""
    if len(message_text.split()) > 1:
        topic_title = message_text.split(' ', 1)[1].strip()
    
    # Check if topic title is empty
    if not topic_title:
        await update.message.reply_text('Нужно указать тему после /add')
        return
    
    # Prepare the data to send to the FastAPI server
    data = {
        "user_id": user_id,
        "topic_title": topic_title
    }
    
    # Send the request to the FastAPI server
    try:
        add_topic_url = f"http://{API_HOST}:{API_PORT}/bot/add_topic"
        async with httpx.AsyncClient() as client:
            response = await client.post(add_topic_url, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Add topic processed: {response_data}")
                
                # Format and send message to the user
                topic_id = response_data['id']
                await update.message.reply_text(
                    f"Тема сохранена: {response_data['title']}\n\n"
                    f"Я подготовлю объяснение этой темы. Скоро вы сможете его увидеть, используя команду /topic {topic_id}"
                )
            else:
                error_text = response.text
                logger.error(f"Error from server: {error_text}")
                await update.message.reply_text('Произошла ошибка при добавлении темы.')
    except Exception as e:
        logger.error(f"Failed to send add topic request to server: {e}")
        await update.message.reply_text('Не удалось связаться с сервером. Попробуйте позже.')

# Define a function to handle the /list command
async def list_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /list command to list user's topics."""
    # Get the user ID
    user_id = update.effective_user.id
    
    # Prepare the data to send to the FastAPI server
    data = {
        "user_id": user_id
    }
    
    # Send the request to the FastAPI server
    try:
        list_topics_url = f"http://{API_HOST}:{API_PORT}/bot/list_topics"
        async with httpx.AsyncClient() as client:
            response = await client.post(list_topics_url, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"List topics processed: {response_data}")
                
                # Format and send message to the user
                topics = response_data.get('topics', [])
                
                if topics:
                    # Format the topics list
                    topics_text = "Ваши темы:\n\n"
                    for topic in topics:
                        topic_id = topic['id']
                        has_explanation = topic.get('explanation') is not None
                        explanation_status = "✅" if has_explanation else "⏳"
                        topics_text += f"{topic_id}. {topic['title']} {explanation_status}\n"
                    
                    # Send the list
                    await update.message.reply_text(topics_text)
                else:
                    # No topics found
                    await update.message.reply_text('У вас пока нет сохраненных тем. Используйте /add <тема> чтобы добавить тему.')
            else:
                error_text = response.text
                logger.error(f"Error from server: {error_text}")
                await update.message.reply_text('Произошла ошибка при получении списка тем.')
    except Exception as e:
        logger.error(f"Failed to send list topics request to server: {e}")
        await update.message.reply_text('Не удалось связаться с сервером. Попробуйте позже.')

# Define a function to handle the /topic command
async def get_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /topic command to get a random topic explanation and remove it."""
    # Get the user ID
    user_id = update.effective_user.id
    
    # Prepare the data to send to the FastAPI server
    data = {
        "user_id": user_id
    }
    
    # Send the request to the FastAPI server
    try:
        random_topic_url = f"http://{API_HOST}:{API_PORT}/bot/random_topic"
        async with httpx.AsyncClient() as client:
            response = await client.post(random_topic_url, json=data)
            
            if response.status_code == 200:
                # Check if we got a topic
                if not response.content or response.content == b'null':
                    await update.message.reply_text('У вас нет сохраненных тем. Используйте /add <тема> чтобы добавить тему для изучения.')
                    return
                
                topic_data = response.json()
                logger.info(f"Random topic processed: {topic_data}")
                
                # Format and send message to the user
                title = topic_data['title']
                explanation = topic_data.get('explanation')
                
                if explanation:
                    # Prepare the message
                    message = f"📚 Тема: {title}\n\n{explanation}\n\n"
                    
                    # Add related topics if available
                    related_topics = topic_data.get('related_topics', [])
                    if related_topics:
                        message += "Смежные темы:\n"
                        for i, related_topic in enumerate(related_topics, 1):
                            message += f"{i}. {related_topic}\n"
                        message += "\nСохранить тему можно командой /add <тема>\n\n"
                    
                    message += f"Эта тема удалена из вашего списка."
                    
                    # Send the message
                    await update.message.reply_text(message)
                else:
                    # No explanation available
                    await update.message.reply_text(
                        f"📚 Тема: {title}\n\n"
                        f"К сожалению, не удалось сгенерировать объяснение для этой темы.\n\n"
                        f"Эта тема удалена из вашего списка. Используйте /add чтобы добавить новые темы."
                    )
            else:
                error_text = response.text
                logger.error(f"Error from server: {error_text}")
                await update.message.reply_text('Произошла ошибка при получении темы.')
    except Exception as e:
        logger.error(f"Failed to send random topic request to server: {e}")
        await update.message.reply_text('Не удалось связаться с сервером. Попробуйте позже.')

# Main function to run the bot
def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token from config.py
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_topic_command))
    application.add_handler(CommandHandler("list", list_topics_command))
    application.add_handler(CommandHandler("topic", get_topic_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
