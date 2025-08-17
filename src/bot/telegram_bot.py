import httpx
import json
import sys
import os
import time
import asyncio

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from env.config import TOKEN, API_HOST, API_PORT
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("BOT")


# Define a function to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received /start command",
        user_id=user_id,
        chat_id=chat_id,
        username=username
    ))
    
    welcome_message = 'Привет, я твой бот! Используй /add <тема> чтобы добавить новую тему для изучения. Используй /list чтобы увидеть свои темы. Используй /topic чтобы получить объяснение случайной темы.'
    
    await update.message.reply_text(welcome_message)
    
    logger.info(format_log_message(
        "Sent welcome message",
        user_id=user_id,
        chat_id=chat_id
    ))      


# Helper function to add a topic
async def add_topic(user_id: int, topic_title: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Add a topic to the database.
    
    Args:
        user_id: The ID of the user
        topic_title: The title of the topic
        chat_id: The ID of the chat to send messages to
        context: The context object
        
    Returns:
        bool: True if the topic was added successfully, False otherwise
    """
    logger.info(format_log_message(
        "Adding topic",
        user_id=user_id,
        chat_id=chat_id,
        topic_title=topic_title
    ))
    
    # Check if topic title is empty
    if not topic_title:
        logger.info(format_log_message(
            "Empty topic title provided",
            user_id=user_id,
            chat_id=chat_id
        ))
        await context.bot.send_message(chat_id=chat_id, text='Нужно указать тему')
        return False
    
    # Prepare the data to send to the FastAPI server
    data = {
        "user_id": user_id,
        "topic_title": topic_title
    }
    
    # Send the request to the FastAPI server
    try:
        add_topic_url = f"http://{API_HOST}:{API_PORT}/bot/add_topic"
        
        logger.info(format_log_message(
            "Sending add_topic request to server",
            url=add_topic_url,
            method="POST",
            payload=data
        ))
        
        async with httpx.AsyncClient() as client:
            response = await client.post(add_topic_url, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(format_log_message(
                    "Topic added successfully",
                    user_id=user_id,
                    topic_id=response_data['id'],
                    topic_title=response_data['title']
                ))
                
                # Format and send message to the user
                topic_id = response_data['id']
                success_message = f"Тема сохранена: {response_data['title']}\n\n" \
                                 f"Я подготовлю объяснение этой темы. Скоро вы сможете его увидеть, используя команду /topic"
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=success_message
                )
                
                logger.info(format_log_message(
                    "Sent success message to user",
                    user_id=user_id,
                    chat_id=chat_id,
                    topic_id=topic_id
                ))
                
                return True
            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when adding topic",
                    status_code=response.status_code,
                    error=error_text,
                    user_id=user_id,
                    topic_title=topic_title
                ))
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text='Произошла ошибка при добавлении темы.'
                )
                
                logger.info(format_log_message(
                    "Sent error message to user",
                    user_id=user_id,
                    chat_id=chat_id
                ))
                
                return False
    except Exception as e:
        logger.error(format_log_message(
            "Failed to send add_topic request to server",
            error=str(e),
            user_id=user_id,
            topic_title=topic_title
        ))
        
        await context.bot.send_message(
            chat_id=chat_id,
            text='Не удалось связаться с сервером. Попробуйте позже.'
        )
        
        logger.info(format_log_message(
            "Sent connection error message to user",
            user_id=user_id,
            chat_id=chat_id
        ))
        
        return False

# Define a function to handle the /add command
async def add_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /add command to add a new topic."""
    # Get the user ID and chat ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    # Get the command text
    message_text = update.message.text
    
    logger.info(format_log_message(
        "Received /add command",
        user_id=user_id,
        chat_id=chat_id,
        username=username,
        command=message_text
    ))
    
    # Extract the topic title (everything after /add)
    topic_title = ""
    if len(message_text.split()) > 1:
        topic_title = message_text.split(' ', 1)[1].strip()
    
    logger.info(format_log_message(
        "Extracted topic title from command",
        user_id=user_id,
        topic_title=topic_title
    ))
    
    # Add the topic
    await add_topic(user_id, topic_title, chat_id, context)

# Define a function to handle the /list command
async def list_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /list command to list user's topics."""
    # Get the user ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received /list command",
        user_id=user_id,
        chat_id=chat_id,
        username=username
    ))
    
    # Prepare the data to send to the FastAPI server
    data = {
        "user_id": user_id
    }
    
    # Send the request to the FastAPI server
    try:
        list_topics_url = f"http://{API_HOST}:{API_PORT}/bot/list_topics"
        
        logger.info(format_log_message(
            "Sending list_topics request to server",
            url=list_topics_url,
            method="POST",
            payload=data
        ))
        
        async with httpx.AsyncClient() as client:
            response = await client.post(list_topics_url, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Format and send message to the user
                topics = response_data.get('topics', [])
                
                logger.info(format_log_message(
                    "Retrieved topics list",
                    user_id=user_id,
                    topic_count=len(topics)
                ))
                
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
                    
                    logger.info(format_log_message(
                        "Sent topics list to user",
                        user_id=user_id,
                        chat_id=chat_id,
                        topic_count=len(topics)
                    ))
                else:
                    # No topics found
                    await update.message.reply_text('У вас пока нет сохраненных тем. Используйте /add <тема> чтобы добавить тему.')
                    
                    logger.info(format_log_message(
                        "Sent empty topics list message to user",
                        user_id=user_id,
                        chat_id=chat_id
                    ))
            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when listing topics",
                    status_code=response.status_code,
                    error=error_text,
                    user_id=user_id
                ))
                
                await update.message.reply_text('Произошла ошибка при получении списка тем.')
                
                logger.info(format_log_message(
                    "Sent error message to user",
                    user_id=user_id,
                    chat_id=chat_id
                ))
    except Exception as e:
        logger.error(format_log_message(
            "Failed to send list_topics request to server",
            error=str(e),
            user_id=user_id
        ))
        
        await update.message.reply_text('Не удалось связаться с сервером. Попробуйте позже.')
        
        logger.info(format_log_message(
            "Sent connection error message to user",
            user_id=user_id,
            chat_id=chat_id
        ))

# Define a function to handle the /topic command
async def get_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /topic command to get a random topic explanation and remove it."""
    # Get the user ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received /topic command",
        user_id=user_id,
        chat_id=chat_id,
        username=username
    ))
    
    # Prepare the data to send to the FastAPI server
    data = {
        "user_id": user_id
    }
    
    # Send the request to the FastAPI server
    try:
        random_topic_url = f"http://{API_HOST}:{API_PORT}/bot/random_topic"
        
        logger.info(format_log_message(
            "Sending random_topic request to server",
            url=random_topic_url,
            method="POST",
            payload=data
        ))
        
        async with httpx.AsyncClient() as client:

            response = await client.post(random_topic_url, json=data, timeout=5)

            logger.info(format_log_message("Retrieved random topic", status_code=response.status_code))
            
            if response.status_code == 200:
                # Check if we got a topic
                if not response.content or response.content == b'null':
                    logger.info(format_log_message(
                        "No topics found for user",
                        user_id=user_id
                    ))
                    
                    await update.message.reply_text('У вас нет сохраненных тем. Используйте /add <тема> чтобы добавить тему для изучения.')
                    
                    logger.info(format_log_message(
                        "Sent no topics message to user",
                        user_id=user_id,
                        chat_id=chat_id
                    ))
                    
                    return
                
                topic_data = response.json()
                
                logger.info(format_log_message(
                    "Retrieved random topic",
                    user_id=user_id,
                    topic_id=topic_data.get('id'),
                    topic_title=topic_data.get('title'),
                    has_explanation=topic_data.get('explanation') is not None
                ))
                
                # Format and send message to the user
                title = topic_data['title']
                explanation = topic_data.get('explanation')
                
                if explanation:
                    # Prepare the message
                    message = f"📚 Тема: {title}\n\n{explanation}\n\n"
                    message += f"Эта тема удалена из вашего списка."
                    
                    # Get related topics if available
                    related_topics = topic_data.get('related_topics', [])
                    
                    if related_topics:
                        # Create keyboard with buttons for each related topic
                        keyboard = []
                        for related_topic in related_topics:
                            # Create a callback data with the topic
                            callback_data = f"add_{related_topic}"
                            keyboard.append([InlineKeyboardButton(
                                related_topic,
                                callback_data=callback_data
                            )])
                        
                        # Add a message about the buttons
                        message += "\n\nВыберите смежную тему для добавления:"
                        
                        # Create the reply markup
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Send the message with buttons
                        await update.message.reply_text(message, reply_markup=reply_markup)
                        
                        logger.info(format_log_message(
                            "Sent topic explanation with related topics buttons to user",
                            user_id=user_id
                        ))
                    else:
                        # Send the message without buttons
                        await update.message.reply_text(message)
                        
                        logger.info(format_log_message(
                            "Sent topic explanation without related topics to user",
                            user_id=user_id
                        ))
                else:
                    # No explanation available
                    # No related topics for topics without explanations
                    no_explanation_message = (
                        f"📚 Тема: {title}\n\n"
                        f"К сожалению, не удалось сгенерировать объяснение для этой темы.\n\n"
                        f"Эта тема удалена из вашего списка. Используйте /add чтобы добавить новые темы."
                    )
                    
                    await update.message.reply_text(no_explanation_message)
                    
                    logger.info(format_log_message(
                        "Sent no explanation message to user",
                        user_id=user_id
                    ))
            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when getting random topic",
                    status_code=response.status_code,
                    error=error_text,
                    user_id=user_id
                ))
                
                await update.message.reply_text('Произошла ошибка при получении темы.')
                
                logger.info(format_log_message(
                    "Sent error message to user",
                    user_id=user_id
                ))
    except Exception as e:
        logger.error(format_log_message(
            "Failed to send random_topic request to server",
            error=str(e),
            user_id=user_id
        ))
        
        await update.message.reply_text('Не удалось связаться с сервером. Попробуйте позже.')
        
        logger.info(format_log_message(
            "Sent connection error message to user",
            user_id=user_id,
            chat_id=chat_id
        ))

# Define a function to handle button clicks
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks for adding related topics."""
    query = update.callback_query
    
    # Get the callback data
    callback_data = query.data
    
    # Get user information
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received callback query",
        user_id=user_id,
        chat_id=chat_id,
        username=username,
        callback_data=callback_data
    ))
    
    # Check if it's an add topic callback
    if callback_data.startswith("add_"):
        # Extract the topic
        topic = callback_data[4:]
        
        logger.info(format_log_message(
            "Extracted topic from callback data",
            user_id=user_id,
            topic=topic
        ))
        
        # Add the topic
        success = await add_topic(user_id, topic, chat_id, context)
        
        # Just answer the callback query with a notification
        if success:
            await query.answer(f"Тема '{topic}' добавлена в ваш список!")
            
            logger.info(format_log_message(
                "Sent success notification for callback query",
                user_id=user_id,
                chat_id=chat_id,
                topic=topic
            ))
        else:
            await query.answer("Не удалось добавить тему")
            
            logger.info(format_log_message(
                "Sent failure notification for callback query",
                user_id=user_id,
                chat_id=chat_id,
                topic=topic
            ))
    else:
        logger.warning(format_log_message(
            "Unknown callback data",
            user_id=user_id,
            callback_data=callback_data
        ))
        
        await query.answer("Неизвестная команда")


# Main function to run the bot
def main() -> None:
    """Start the bot."""
    logger.info(format_log_message(
        "Starting Telegram bot",
        api_host=API_HOST,
        api_port=API_PORT
    ))
    
    # Create the Application and pass it your bot's token from config.py
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_topic_command))
    application.add_handler(CommandHandler("list", list_topics_command))
    application.add_handler(CommandHandler("topic", get_topic_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info(format_log_message(
        "Handlers registered, starting polling"
    ))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info(format_log_message(
        "Bot stopped"
    ))

if __name__ == '__main__':
    main()
