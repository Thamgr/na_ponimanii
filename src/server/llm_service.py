"""
LLM Service Module

This module provides functions to interact with an external LLM service
for generating explanations of topics.
"""
import re
import os
import sys
from typing import Optional, List

# Add parent directory to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.messages import AIMessage
import httpx

from env.config import (
    LLM_API_KEY,
    LLM_API_BASE,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    EXPLANATION_SYSTEM_PROMPT,
    EXPLANATION_USER_PROMPT_TEMPLATE,
    RELATED_TOPICS_SYSTEM_PROMPT,
    RELATED_TOPICS_USER_PROMPT_TEMPLATE,
)
from tools.logging_config import setup_logging, format_log_message

# Set up component-specific logger
logger = setup_logging("LLM")

class LLMServiceException(Exception):
    """Exception raised for errors in the LLM service."""
    pass

def get_llm_client() -> ChatOpenAI:
    """
    Create and return a ChatOpenAI client.
    
    Returns:
        ChatOpenAI: A configured LLM client
        
    Raises:
        LLMServiceException: If the API key is not set
    """
    if not LLM_API_KEY:
        raise LLMServiceException("LLM API key is not set. Please set the LLM_API_KEY environment variable.")
    
    try:
        return ChatOpenAI(
            openai_api_base=LLM_API_BASE,
            openai_api_key=LLM_API_KEY,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
    except Exception as e:
        logger.error(format_log_message(
            "Error creating LLM client",
            error=str(e),
            error_type=type(e).__name__
        ))
        raise LLMServiceException(f"Failed to initialize LLM client: {str(e)}")

def generate_explanation(topic: str) -> str:
    """
    Generate an explanation for a given topic using an external LLM.
    
    Args:
        topic (str): The topic to explain
        
    Returns:
        str: The generated explanation
        
    Raises:
        LLMServiceException: If there's an error communicating with the LLM service
    """
    try:
        # Format the user prompt with the topic (now just the topic itself)
        user_prompt = EXPLANATION_USER_PROMPT_TEMPLATE.format(topic=topic)
        
        # Create messages for the LLM (system prompt contains all format instructions)
        messages = [
            SystemMessage(content=EXPLANATION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        
        # Get the LLM client
        llm = get_llm_client()
        
        # Send the request to the LLM
        logger.info(format_log_message(
            "Sending request to LLM for explanation",
            topic=topic,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS
        ))
        
        response = llm.invoke(messages)
        
        # Extract and return the content
        if isinstance(response, AIMessage):
            explanation = response.content
            
            # Clean the explanation from HTML tags
            explanation = clean_html_tags(explanation)
            
            logger.info(format_log_message(
                "Received explanation from LLM",
                topic=topic,
                explanation_length=len(explanation) if explanation else 0
            ))
            
            return explanation
        else:
            logger.error(format_log_message(
                "Unexpected response type from LLM",
                topic=topic,
                response_type=str(type(response))
            ))
            
            return "Извините, не удалось сгенерировать объяснение. Попробуйте позже."
            
    except httpx.TimeoutException:
        logger.error(format_log_message(
            "Timeout while requesting explanation from LLM",
            topic=topic,
            model=LLM_MODEL
        ))
        
        raise LLMServiceException("Превышено время ожидания ответа от сервиса. Попробуйте позже.")
    
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        
        logger.error(format_log_message(
            "HTTP error while requesting explanation from LLM",
            topic=topic,
            status_code=status_code,
            error=str(e)
        ))
        
        if 400 <= status_code < 500:
            raise LLMServiceException(f"Ошибка в запросе к сервису (код {status_code}). Пожалуйста, сообщите администратору.")
        else:
            raise LLMServiceException(f"Ошибка сервиса (код {status_code}). Попробуйте позже.")
    
    except Exception as e:
        logger.error(format_log_message(
            "Error generating explanation",
            topic=topic,
            error=str(e),
            error_type=type(e).__name__
        ))
        
        raise LLMServiceException(f"Произошла ошибка при генерации объяснения: {str(e)}")

def generate_related_topics(topic: str) -> List[str]:
    """
    Generate a list of related topics for a given topic using an external LLM.
    
    Args:
        topic (str): The topic to generate related topics for
        
    Returns:
        List[str]: A list of related topics
        
    Raises:
        LLMServiceException: If there's an error communicating with the LLM service
    """
    try:
        # Format the user prompt with the topic
        user_prompt = RELATED_TOPICS_USER_PROMPT_TEMPLATE.format(topic=topic)
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=RELATED_TOPICS_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        
        # Get the LLM client
        llm = get_llm_client()
        
        # Send the request to the LLM
        logger.info(format_log_message(
            "Sending request to LLM for related topics",
            topic=topic,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS
        ))
        
        response = llm.invoke(messages)
        
        # Extract and return the content
        if isinstance(response, AIMessage):
            content = response.content
            
            # Clean the content from HTML tags
            content = clean_html_tags(content)
            
            # Parse the content into a list of topics
            topics = parse_topics_from_text(content)
            
            logger.info(format_log_message(
                "Received related topics from LLM",
                topic=topic,
                related_topics_count=len(topics)
            ))
            
            return topics
        else:
            logger.error(format_log_message(
                "Unexpected response type from LLM",
                topic=topic,
                response_type=str(type(response))
            ))
            
            return []
            
    except httpx.TimeoutException:
        logger.error(format_log_message(
            "Timeout while requesting related topics from LLM",
            topic=topic,
            model=LLM_MODEL
        ))
        
        return []
    
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        
        logger.error(format_log_message(
            "HTTP error while requesting related topics from LLM",
            topic=topic,
            status_code=status_code,
            error=str(e)
        ))
        
        return []
    
    except Exception as e:
        logger.error(format_log_message(
            "Error generating related topics",
            topic=topic,
            error=str(e),
            error_type=type(e).__name__
        ))
        
        return []

def parse_topics_from_text(text: str) -> List[str]:
    """
    Parse a list of topics from text.
    
    Args:
        text (str): The text to parse
        
    Returns:
        List[str]: A list of topics
    """
    # Split the text by newlines
    lines = text.strip().split('\n')
    
    # Clean up each line
    topics = []
    for line in lines:
        # Remove any leading numbers, bullets, or other markers
        line = re.sub(r'^[\d\-\*\•\.\s]+', '', line.strip())
        
        # Remove any trailing punctuation
        line = re.sub(r'[,\.;:]$', '', line)
        
        # Skip empty lines
        if line:
            topics.append(line)
    
    return topics

def clean_html_tags(text: str) -> str:
    """
    Clean HTML tags from text to avoid parsing issues.
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: The cleaned text
    """
    # Replace <think> tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Replace other potentially problematic tags
    # text = re.sub(r'<(?!b>|/b>|i>|/i>|code>|/code>|pre>|/pre>)[^>]*>', '', text)
    
    return text

if __name__ == "__main__":
    # Simple test if run directly
    try:
        logger.info(format_log_message(
            "Running LLM service test",
            test_topic="Python programming"
        ))
        
        explanation = generate_explanation("Python programming")
        
        logger.info(format_log_message(
            "LLM service test completed successfully",
            explanation_length=len(explanation) if explanation else 0
        ))
        
        print(explanation)
    except LLMServiceException as e:
        logger.error(format_log_message(
            "LLM service test failed",
            error=str(e)
        ))
        
        print(f"Error: {e}")