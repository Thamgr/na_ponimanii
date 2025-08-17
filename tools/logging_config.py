import logging
import os
import json
from datetime import datetime

# Configure logging directory
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Configure log file name with timestamp
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"app_{current_time}.log")

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configure logging level
LOG_LEVEL = logging.INFO

def setup_logging(component_name):
    """
    Set up logging for a specific component.
    
    Args:
        component_name: The name of the component (e.g., "BOT", "SERVER", "LLM")
        
    Returns:
        A configured logger instance
    """
    # Create logger
    logger = logging.getLogger(component_name)
    logger.setLevel(LOG_LEVEL)
    
    # Create file handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(LOG_LEVEL)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def format_log_message(message, **kwargs):
    """
    Format a log message with additional context.
    
    Args:
        message: The main log message
        **kwargs: Additional context to include in the log
        
    Returns:
        A formatted log message with context as JSON
    """
    # Create a dictionary with the message and context
    log_data = {
        "message": message
    }
    
    # Add additional context
    if kwargs:
        log_data["context"] = kwargs
    
    # Format as JSON
    try:
        return json.dumps(log_data)
    except Exception:
        # Fallback if JSON serialization fails
        return f"{message} | Context: {str(kwargs)}"