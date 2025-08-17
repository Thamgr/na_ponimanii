import httpx
import json
import sys
import os
import time
import asyncio
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
    BOT_TOPIC_ADDED_ERROR, BOT_CONNECTION_ERROR, BOT_TOPIC_PROMPT,
    BOT_TOPIC_PROMPT_AGAIN, BOT_NO_TOPICS, BOT_TOPICS_LIST_HEADER,
    BOT_TOPICS_LIST_ERROR, BOT_NO_TOPICS_FOR_EXPLANATION, BOT_TOPIC_EXPLANATION,
    BOT_RELATED_TOPICS_PROMPT, BOT_NO_EXPLANATION, BOT_TOPIC_ERROR,
    BOT_TOPIC_ADDED_FROM_CALLBACK, BOT_TOPIC_ADDED_FROM_CALLBACK_ERROR,
    BOT_UNKNOWN_COMMAND, BOT_KEYBOARD_ADD_TOPIC, BOT_KEYBOARD_STUDY_TOPIC,
    BOT_KEYBOARD_WHAT_NEXT, BOT_THINKING_MESSAGE
)
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("BOT")

# Define conversation states
WAITING_FOR_TOPIC = 1


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
            text=BOT_THINKING_MESSAGE
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
    Create a keyboard with both default buttons.
    
    Returns:
        ReplyKeyboardMarkup: The keyboard markup with both buttons
    """
    # Always include both buttons
    keyboard = [
        [KeyboardButton(BOT_KEYBOARD_ADD_TOPIC), KeyboardButton(BOT_KEYBOARD_STUDY_TOPIC)]
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
            parent_topic_title=parent_topic_title
        ))
        
        async with httpx.AsyncClient() as client:
            response = await client.post(add_topic_url, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(format_log_message(
                    "Topic added successfully",
                    user_id=user_id,
                    topic_id=response_data['id'],
                    topic_title=response_data['title'],
                    parent_topic_title=parent_topic_title
                ))
                
                return True, response_data
            else:
                error_text = response.text
                logger.error(format_log_message(
                    "Error response from server when adding topic",
                    status_code=response.status_code,
                    error=error_text,
                    user_id=user_id,
                    topic_title=topic_title,
                    parent_topic_title=parent_topic_title
                ))
                
                return False, None
    except Exception as e:
        logger.error(format_log_message(
            "Failed to send add_topic request to server",
            error=str(e),
            user_id=user_id,
            topic_title=topic_title,
            parent_topic_title=parent_topic_title
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
        topic_title=topic_title,
        parent_topic_title=parent_topic_title
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
        
        return False

# Define a function to handle the /add command
@thinking_decorator
async def add_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /add command to start the topic addition process."""
    # Get the user ID and chat ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received /add command",
        user_id=user_id,
        chat_id=chat_id,
        username=username
    ))
    
    # Prompt the user for a topic
    await update.message.reply_text(BOT_TOPIC_PROMPT)
    
    logger.info(format_log_message(
        "Sent topic prompt to user",
        user_id=user_id,
        chat_id=chat_id
    ))
    
    # Return the state to indicate we're waiting for a topic
    return WAITING_FOR_TOPIC

# Define a function to handle the topic response
@thinking_decorator
async def receive_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's response with the topic."""
    # Get the user ID and chat ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    # Get the topic from the message
    topic_title = update.message.text.strip()
    
    logger.info(format_log_message(
        "Received topic from user",
        user_id=user_id,
        chat_id=chat_id,
        username=username,
        topic_title=topic_title
    ))
    
    # Add the topic (no parent topic for topics added directly by the user)
    success = await add_topic(user_id, topic_title, chat_id, context, parent_topic_title=None)
    
    # Create keyboard with two buttons
    reply_markup = create_keyboard()
    
    # If the topic was added successfully, show the keyboard again
    if success:
        await update.message.reply_text(
            BOT_KEYBOARD_WHAT_NEXT,
            reply_markup=reply_markup
        )
    
    # End the conversation
    return ConversationHandler.END

# Define a function to handle the case when a user presses the add topic button while in the waiting for topic state
@thinking_decorator
async def handle_add_topic_in_waiting_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the case when a user presses the add topic button while in the waiting for topic state."""
    # Get the user ID and chat ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received add topic button press while in waiting for topic state",
        user_id=user_id,
        chat_id=chat_id,
        username=username
    ))
    
    # Prompt the user for a topic again
    await update.message.reply_text(BOT_TOPIC_PROMPT_AGAIN)
    
    # Stay in the conversation
    return WAITING_FOR_TOPIC

# Define a function to handle the case when a user presses the study topic button while in the waiting for topic state
@thinking_decorator
async def handle_study_topic_in_waiting_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the case when a user presses the study topic button while in the waiting for topic state."""
    # Get the user ID and chat ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(format_log_message(
        "Received study topic button press while in waiting for topic state",
        user_id=user_id,
        chat_id=chat_id,
        username=username
    ))
    
    # End the conversation
    await get_topic_command(update, context)
    
    # End the conversation
    return ConversationHandler.END

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
        
        await update.message.reply_text(BOT_CONNECTION_ERROR)

# Define a function to handle the /topic command
@thinking_decorator
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
                    topic_title=topic_data.get('title'),
                    has_explanation=topic_data.get('explanation') is not None
                ))
                
                # Format and send message to the user
                title = topic_data['title']
                explanation = topic_data.get('explanation')
                
                if explanation:
                    # Prepare the message
                    message = BOT_TOPIC_EXPLANATION.format(title=title, explanation=explanation)
                    
                    # Get related topics if available
                    related_topics = topic_data.get('related_topics', [])
                    
                    if related_topics:
                        # Create keyboard with buttons for each related topic
                        keyboard = []
                        for related_topic in related_topics:
                            # Create a callback data with the topic and parent topic title
                            callback_data = f"add_{related_topic}|{title}"
                            keyboard.append([InlineKeyboardButton(
                                related_topic,
                                callback_data=callback_data
                            )])
                        
                        # Add a message about the buttons
                        message += BOT_RELATED_TOPICS_PROMPT
                        
                        # Create the reply markup
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Send the message with inline buttons
                        await update.message.reply_text(message, reply_markup=reply_markup)
                        
                        # Create keyboard with two buttons
                        reply_markup = create_keyboard()
                        
                        # Show the keyboard again
                        await update.message.reply_text(BOT_KEYBOARD_WHAT_NEXT, reply_markup=reply_markup)
                    else:
                        # Send the message without inline buttons
                        await update.message.reply_text(message)
                        
                        # Create keyboard with two buttons
                        reply_markup = create_keyboard()
                        
                        # Show the keyboard again
                        await update.message.reply_text(BOT_KEYBOARD_WHAT_NEXT, reply_markup=reply_markup)
                else:
                    # No explanation available
                    # No related topics for topics without explanations
                    no_explanation_message = BOT_NO_EXPLANATION.format(title=title)
                    
                    await update.message.reply_text(no_explanation_message)
                    
                    # Create keyboard with two buttons
                    reply_markup = create_keyboard()
                    
                    # Show the keyboard again
                    await update.message.reply_text(BOT_KEYBOARD_WHAT_NEXT, reply_markup=reply_markup)

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
        
        await update.message.reply_text(BOT_CONNECTION_ERROR)


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
            # Extract the topic and parent topic title
            parts = callback_data[4:].split('|')
            topic = parts[0]
            parent_topic_title = parts[1] if len(parts) > 1 else None
            
            logger.info(format_log_message(
                "Parsed callback data",
                topic=topic,
                parent_topic_title=parent_topic_title
            ))
            
            # Send the request to the server using the common function
            success, _ = await send_add_topic_request(user_id, topic, parent_topic_title)
        except Exception as e:
            logger.error(format_log_message(
                "Error processing add topic callback",
                error=str(e),
                error_type=type(e).__name__,
                callback_data=callback_data
            ))
            success = False
            
        # Answer the callback query with a notification
        if success and topic:
            await query.answer(BOT_TOPIC_ADDED_FROM_CALLBACK.format(topic=topic))
        else:
            await query.answer(BOT_TOPIC_ADDED_FROM_CALLBACK_ERROR)
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

    # Create conversation handler for adding topics
    add_topic_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_topic_command),
            MessageHandler(filters.Regex(f"^{BOT_KEYBOARD_ADD_TOPIC}$"), add_topic_command)
        ],
        states={
            WAITING_FOR_TOPIC: [
                MessageHandler(
                    filters.Regex(f"^{BOT_KEYBOARD_ADD_TOPIC}$"),
                    handle_add_topic_in_waiting_state
                ),
                MessageHandler(
                    filters.Regex(f"^{BOT_KEYBOARD_STUDY_TOPIC}$"),
                    handle_study_topic_in_waiting_state
                ),
                MessageHandler(
                    filters.TEXT &
                    ~filters.COMMAND,  # Exclude all commands
                    receive_topic
                )
            ]
        },
        fallbacks=[MessageHandler(filters.COMMAND, lambda update, context: ConversationHandler.END)]
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    # Add handler for keyboard buttons
    application.add_handler(add_topic_conv_handler)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f"^{BOT_KEYBOARD_STUDY_TOPIC}$"),
        handle_keyboard_buttons
    ))
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

