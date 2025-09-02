import httpx
import json
import sys
import os
import time
import asyncio
import random
from typing import Tuple, Dict, Optional

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from env.config import (
    TOKEN, API_HOST, API_PORT,
    BOT_WELCOME_MESSAGE, BOT_EMPTY_TOPIC_ERROR, BOT_TOPIC_ADDED_SUCCESS,
    BOT_TOPIC_ADDED_ERROR, BOT_CONNECTION_ERROR, BOT_NO_TOPICS, BOT_TOPICS_LIST_HEADER,
    BOT_TOPICS_LIST_ERROR, BOT_NO_TOPICS_FOR_EXPLANATION, BOT_TOPIC_EXPLANATION,
    BOT_RELATED_TOPICS_PROMPT, BOT_NO_EXPLANATION, BOT_TOPIC_ERROR,
    BOT_TOPIC_ADDED_FROM_CALLBACK, BOT_TOPIC_ADDED_FROM_CALLBACK_ERROR,
    BOT_UNKNOWN_COMMAND, BOT_THINKING_MESSAGE_VARIANTS, BOT_KEYBOARD_STUDY_TOPIC,
    BOT_KEYBOARD_WHAT_NEXT, BOT_THINKING_MESSAGE, BOT_TOPIC_LENGTH_ERROR
)

from tools.logging_config import setup_logging, format_log_message
from metrics.metrics import get_metrics_client

# Set up component-specific logger
logger = setup_logging("BOT")

# Define conversation states
WAITING_FOR_TOPIC = 1

# Global maps to store topic data
# Map for parent topics - Key: related_topic, Value: parent_topic_title
parent_topic_map = {}

# Map for related topics - Key: topic_id, Value: related_topic
# This helps keep callback_data short
related_topic_map = {}

# Counter for generating unique IDs for related topics
related_topic_counter = 0


# Decorator for handlers to show and remove "Thinking..." message
def thinking_decorator(handler_func):
    """
    Decorator that shows a "Thinking..." message at the start of a handler
    and removes it when the handler finishes.
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Get the chat ID
        chat_id = update.effective_chat.id
        
        # Send the "Thinking..." message
        thinking_message = await context.bot.send_message(
            chat_id=chat_id,
            text=random.choice(BOT_THINKING_MESSAGE_VARIANTS)
        )
        
        # Store the message ID in the context
        if not context.user_data.get('thinking_messages'):
            context.user_data['thinking_messages'] = []
        
        context.user_data['thinking_messages'].append(thinking_message.message_id)
        
        # Call the handler function
        result = await handler_func(update, context, *args, **kwargs)
        
        # Delete the "Thinking..." message
        if context.user_data.get('thinking_messages'):
            message_id = context.user_data['thinking_messages'].pop()
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.error(format_log_message(
                    "Failed to delete thinking message",
                    error=str(e),
                    chat_id=chat_id,
                    message_id=message_id
                ))
        
        return result
    
    return wrapper


# Helper function to create keyboards
def create_keyboard():
    """
    Create a keyboard with the study topic button.
    
    Returns:
        ReplyKeyboardMarkup: The keyboard markup with the study button
    """
    # Only include the study topic button
    keyboard = [
        [KeyboardButton(BOT_KEYBOARD_STUDY_TOPIC)]
    ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Define a function to handle the /start command
@thinking_decorator
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
    
    # Create keyboard with two buttons
    reply_markup = create_keyboard()
    
    # Send welcome message with keyboard
    await update.message.reply_text(BOT_WELCOME_MESSAGE, reply_markup=reply_markup)


# Helper function to send add_topic request to the server
async def send_add_topic_request(user_id: int, topic_title: str, parent_topic_title: Optional[str] = None) -> Tuple[bool, Optional[Dict]]:
    """
    Send a request to the server to add a topic.
    
    Args:
        user_id: The ID of the user
        topic_title: The title of the topic
        parent_topic_title: The title of the parent topic, if available
        
    Returns:
        Tuple[bool, Optional[Dict]]: A tuple containing a success flag and the response data if successful
    """
    # Prepare the data to send to the FastAPI server
    data = {
        "user_id": user_id,
        "topic_title": topic_title
    }
    
    # Add parent_topic_title if provided
    if parent_topic_title:
        data["parent_topic_title"] = parent_topic_title
    
    # Send the request to the FastAPI server
    try:
        add_topic_url = f"http://{API_HOST}:{API_PORT}/bot/add_topic"
        
        logger.info(format_log_message(
            "Sending add_topic request to server",
            url=add_topic_url,
            method="POST",
            payload=data,
        ))
        
        async with httpx.AsyncClient() as client:
            response = await client.post(add_topic_url, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(format_log_message(
                    "Topic added successfully",
                    user_id=user_id,
                    topic_id=response_data['id'],
                ))
                
                return True, response_data
            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when adding topic",
                    status_code=response.status_code,
                    error=error_text,
                    user_id=user_id,
                ))
                
                return False, None
    except Exception as e:
        logger.error(format_log_message(
            "Failed to send add_topic request to server",
            error=str(e),
            user_id=user_id,
        ))
        
        return False, None

# Helper function to add a topic
async def add_topic(user_id: int, topic_title: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, parent_topic_title: Optional[str] = None) -> bool:
    """
    Add a topic to the database.
    
    Args:
        user_id: The ID of the user
        topic_title: The title of the topic
        chat_id: The ID of the chat to send messages to
        context: The context object
        parent_topic_title: The title of the parent topic, if available
        
    Returns:
        bool: True if the topic was added successfully, False otherwise
    """
    logger.info(format_log_message(
        "Adding topic",
        user_id=user_id,
        chat_id=chat_id,
    ))
    
    # Check if topic title is empty
    if not topic_title:
        logger.info(format_log_message(
            "Empty topic title provided",
            user_id=user_id,
            chat_id=chat_id
        ))
        await context.bot.send_message(chat_id=chat_id, text=BOT_EMPTY_TOPIC_ERROR)
        return False
    
    # Send the request to the server
    success, response_data = await send_add_topic_request(user_id, topic_title, parent_topic_title)
    
    if success:
        # Format and send message to the user
        success_message = BOT_TOPIC_ADDED_SUCCESS.format(title=response_data['title'])
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=success_message
        )
        
        return True
    else:
        # Send error message to the user
        await context.bot.send_message(
            chat_id=chat_id,
            text=BOT_TOPIC_ADDED_ERROR
        )
        get_metrics_client().incr(f'responses.{500}.None.add_topic')
        
        return False


# Define a function to handle the /list command
@thinking_decorator
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
                    topics_text = BOT_TOPICS_LIST_HEADER
                    for topic in topics:
                        topic_id = topic['id']
                        has_explanation = topic.get('explanation') is not None
                        explanation_status = "✅" if has_explanation else "⏳"
                        topics_text += f"{topic_id}. {topic['title']} {explanation_status}\n"
                    
                    # Send the list
                    await update.message.reply_text(topics_text)
                    
                    # Create keyboard with two buttons
                    reply_markup = create_keyboard()
                    
                    # Show the keyboard again
                    await update.message.reply_text(BOT_KEYBOARD_WHAT_NEXT, reply_markup=reply_markup)
                else:
                    # No topics found
                    # Create keyboard with both buttons
                    reply_markup = create_keyboard()
                    
                    # Send message with keyboard
                    await update.message.reply_text(BOT_NO_TOPICS, reply_markup=reply_markup)
            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when listing topics",
                    status_code=response.status_code,
                    error=error_text,
                    user_id=user_id
                ))
                
                await update.message.reply_text(BOT_TOPICS_LIST_ERROR)

    except Exception as e:
        logger.error(format_log_message(
            "Failed to send list_topics request to server",
            error=str(e),
            user_id=user_id
        ))
        get_metrics_client().incr(f'responses.{500}.None.list_topics')
        
        await update.message.reply_text(BOT_CONNECTION_ERROR)

# Define a function to handle the /topic command
@thinking_decorator
async def get_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /topic command to get a random topic explanation and then delete it."""
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
            # Initialize response variable
            response = None
            
            try:
                response = await client.post(random_topic_url, json=data, timeout=10)
            except Exception as err:
                logger.error(format_log_message(
                    "Error retrieving random topic",
                    error=str(err),
                    user_id=user_id
                ))
                await update.message.reply_text(BOT_CONNECTION_ERROR)
                return
            
            # Check if response is valid
            if response is None:
                logger.error(format_log_message(
                    "No response received from server",
                    user_id=user_id
                ))
                await update.message.reply_text(BOT_CONNECTION_ERROR)
                return
                
            if response.status_code == 200:
                # Check if we got a topic
                if not response.content or response.content == b'null':
                    logger.info(format_log_message(
                        "No topics found for user",
                        user_id=user_id
                    ))
                    
                    # Create keyboard with both buttons
                    reply_markup = create_keyboard()
                    
                    # Send message with keyboard
                    await update.message.reply_text(BOT_NO_TOPICS_FOR_EXPLANATION, reply_markup=reply_markup)
                    
                    return
                
                topic_data = response.json()
                
                logger.info(format_log_message(
                    "Retrieved random topic",
                    user_id=user_id,
                    topic_id=topic_data.get('id'),
                    has_explanation=topic_data.get('explanation') is not None
                ))
                
                # Get the topic ID for later deletion
                topic_id = topic_data.get('id')
                
                # Format and send message to the user
                title = topic_data['title']
                explanation = topic_data.get('explanation')
                assert explanation

                # Prepare the message
                message = BOT_TOPIC_EXPLANATION.format(title=title, explanation=explanation)
                
                # Get related topics if available
                related_topics = topic_data.get('related_topics', [])
                
                # Create keyboard with buttons for each related topic
                keyboard = []
                # Get a global reference to the counter
                global related_topic_counter
                
                for related_topic in related_topics:
                    # Store the parent topic in the global map
                    parent_topic_map[related_topic] = title
                    
                    # Generate a unique ID for this related topic
                    related_topic_id = related_topic_counter
                    related_topic_counter += 1
                    
                    # Store the related topic in the map with its ID
                    related_topic_map[related_topic_id] = related_topic
                    
                    # Create a short callback data with just the ID
                    callback_data = f"add_{related_topic_id}"
                    keyboard.append([InlineKeyboardButton(
                        related_topic,
                        callback_data=callback_data
                    )])
                    
                    logger.info(format_log_message(
                        "Stored topic in maps",
                        topic_id=topic_id,
                        related_topic=related_topic,
                        parent_topic=title
                    ))
                
                if related_topics:
                    # Add a message about the buttons
                    message += BOT_RELATED_TOPICS_PROMPT
                    
                    # Create the reply markup
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send the message with inline buttons
                    await update.message.reply_text(message, reply_markup=reply_markup)
                else:
                    # Send the message without inline buttons
                    await update.message.reply_text(message)
                    
                # Create keyboard with two buttons
                reply_markup = create_keyboard()
                
                # Show the keyboard again
                await update.message.reply_text(BOT_KEYBOARD_WHAT_NEXT, reply_markup=reply_markup)
                
                # Delete the topic after displaying it
                if topic_id:
                    logger.info(format_log_message(
                        "Deleting topic after displaying",
                        topic_id=topic_id
                    ))
                    
                    success = await send_delete_topic_request(topic_id)
                    
                    if not success:
                        logger.warning(format_log_message(
                            "Failed to delete topic after displaying",
                            topic_id=topic_id
                        ))
                        # Continue even if deletion fails - this is not critical for the user experience

            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when getting random topic",
                    status_code=response.status_code,
                    error=error_text,
                    user_id=user_id
                ))
                
                await update.message.reply_text(BOT_TOPIC_ERROR)

    except Exception as e:
        logger.error(format_log_message(
            "Failed to send random_topic request to server",
            error=str(e),
            user_id=user_id
        ))
        get_metrics_client().incr(f'responses.{500}.None.get_topic')
        
        await update.message.reply_text(BOT_CONNECTION_ERROR)


# Helper function to send delete_topic request to the server
async def send_delete_topic_request(topic_id: int) -> bool:
    """
    Send a request to the server to delete a topic.
    
    Args:
        topic_id: The ID of the topic to delete
        
    Returns:
        bool: True if the topic was deleted successfully, False otherwise
    """
    # Prepare the data to send to the FastAPI server
    data = {
        "topic_id": topic_id
    }
    
    # Send the request to the FastAPI server
    try:
        delete_topic_url = f"http://{API_HOST}:{API_PORT}/bot/delete_topic"
        
        logger.info(format_log_message(
            "Sending delete_topic request to server",
            url=delete_topic_url,
            method="POST",
            payload=data,
            topic_id=topic_id
        ))
        
        async with httpx.AsyncClient() as client:
            response = await client.post(delete_topic_url, json=data)
            
            if response.status_code == 200:
                logger.info(format_log_message(
                    "Topic deleted successfully",
                    topic_id=topic_id
                ))
                
                return True
            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when deleting topic",
                    status_code=response.status_code,
                    error=error_text,
                    topic_id=topic_id
                ))
                
                return False
    except Exception as e:
        logger.error(format_log_message(
            "Failed to send delete_topic request to server",
            error=str(e),
            topic_id=topic_id
        ))
        
        return False


# Define a function to handle button clicks
@thinking_decorator
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
    
    # Default success value
    success = False
    topic = None
    
    # Check if it's an add topic callback
    if callback_data.startswith("add_"):
        try:
            # Extract the topic ID
            topic_id_str = callback_data[4:]
            topic_id = int(topic_id_str)
            
            # Get the topic from the related topics map
            topic = related_topic_map.get(topic_id)
            assert topic
            
            # Get the parent topic from the global map
            parent_topic_title = parent_topic_map.get(topic)
            
            logger.info(format_log_message(
                "Retrieved topic from maps",
                topic_id=topic_id,
            ))
            
            # Send the request to the server using the common function
            success, _ = await send_add_topic_request(user_id, topic, parent_topic_title)
            assert success
            
            await query.answer(BOT_TOPIC_ADDED_FROM_CALLBACK.format(topic=topic))
        except Exception as e:
            logger.error(format_log_message(
                "Error processing add topic callback",
                error=str(e),
                error_type=type(e).__name__,
                callback_data=callback_data
            ))
            await query.answer(BOT_TOPIC_ADDED_FROM_CALLBACK_ERROR)
            get_metrics_client().incr(f'responses.{500}.None.add_button')
            success = False
    else:
        # Not a recognized callback
        await query.answer(BOT_UNKNOWN_COMMAND)


# Define a function to handle keyboard button presses
async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle keyboard button presses."""
    # Get the message text
    message_text = update.message.text
    
    # Get user information
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received keyboard button press",
        user_id=user_id,
        chat_id=chat_id,
        username=username,
        button=message_text
    ))
    
    # Handle the button press
    if message_text == BOT_KEYBOARD_STUDY_TOPIC:
        # Call the get_topic_command function
        return await get_topic_command(update, context)
    else:
        # Unknown button
        logger.warning(format_log_message(
            "Unknown keyboard button in handler",
            user_id=user_id,
            button=message_text
        ))


# Define a function to handle direct messages as topics
@thinking_decorator
async def handle_direct_message_as_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any direct message as a topic to add."""
    # Get the user ID and chat ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    # Get the topic from the message
    topic_title = update.message.text.strip()
    
    logger.info(format_log_message(
        "Received direct message as topic",
        user_id=user_id,
        chat_id=chat_id,
        username=username,
    ))
    
    # Check if topic length is valid (between 3 and 30 characters)
    if len(topic_title) < 3 or len(topic_title) > 30:
        logger.info(format_log_message(
            "Invalid topic length",
            user_id=user_id,
            chat_id=chat_id,
            topic_length=len(topic_title)
        ))
        
        # Create keyboard with study topic button
        reply_markup = create_keyboard()
        
        # Send error message
        await update.message.reply_text(
            BOT_TOPIC_LENGTH_ERROR,
            reply_markup=reply_markup
        )
        return
    
    # Add the topic (no parent topic for topics added directly by the user)
    success = await add_topic(user_id, topic_title, chat_id, context, parent_topic_title=None)
    
    # Create keyboard with study topic button
    reply_markup = create_keyboard()
    
    # If the topic was added successfully, show the keyboard again
    if success:
        await update.message.reply_text(
            BOT_KEYBOARD_WHAT_NEXT,
            reply_markup=reply_markup
        )

# Function to clean up the topic maps
async def cleanup_topic_maps(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodically clean up the topic maps to avoid memory leaks."""
    global parent_topic_map, related_topic_map, related_topic_counter
    
    logger.info(format_log_message(
        "Cleaning up topic maps",
        parent_map_size=len(parent_topic_map),
        related_map_size=len(related_topic_map)
    ))
    
    # Clear the maps
    parent_topic_map = {}
    related_topic_map = {}
    related_topic_counter = 0
    
    logger.info(format_log_message(
        "Topic maps cleaned up"
    ))

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
    # Add handler for keyboard buttons
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f"^{BOT_KEYBOARD_STUDY_TOPIC}$"),
        handle_keyboard_buttons
    ))
    # Add handler for any text message that isn't a command or the study topic button
    # This will treat any regular message as a topic to add
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(f"^{BOT_KEYBOARD_STUDY_TOPIC}$"),
        handle_direct_message_as_topic
    ))
    application.add_handler(CommandHandler("list", list_topics_command))
    application.add_handler(CommandHandler("topic", get_topic_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    
    # Try to add job to clean up parent topic map every hour
    # Note: This requires the job-queue extra: pip install "python-telegram-bot[job-queue]"
    try:
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(cleanup_topic_maps, interval=3600, first=3600)
            logger.info(format_log_message(
                "Handlers registered, cleanup job scheduled, starting polling"
            ))
        else:
            logger.warning(format_log_message(
                "JobQueue not available, cleanup job not scheduled"
            ))
            logger.info(format_log_message(
                "Handlers registered, starting polling"
            ))
    except Exception as e:
        logger.error(format_log_message(
            "Error setting up job queue",
            error=str(e),
            error_type=type(e).__name__
        ))
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

