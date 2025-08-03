"""
LLM Service Module

This module provides functions to interact with an external LLM service
for generating explanations of topics.
"""
import re

import logging
import os
from typing import Optional

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.messages import AIMessage
import httpx

from config import (
    LLM_API_KEY,
    LLM_API_BASE,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    EXPLANATION_SYSTEM_PROMPT,
    EXPLANATION_USER_PROMPT_TEMPLATE,
)

# Set up logging
logger = logging.getLogger(__name__)

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
        logger.error(f"Error creating LLM client: {e}")
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
        logger.info(f"Sending request to LLM for topic: {topic}")
        response = llm.invoke(messages)
        
        # Extract and return the content
        if isinstance(response, AIMessage):
            explanation = response.content
            
            # Clean the explanation from HTML tags
            explanation = clean_html_tags(explanation)
            
            logger.info(f"Received explanation for topic: {topic}")
            return explanation
        else:
            logger.error(f"Unexpected response type: {type(response)}")
            return "Извините, не удалось сгенерировать объяснение. Попробуйте позже."
            
    except httpx.TimeoutException:
        logger.error(f"Timeout while requesting explanation for topic: {topic}")
        raise LLMServiceException("Превышено время ожидания ответа от сервиса. Попробуйте позже.")
    
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        logger.error(f"HTTP error {status_code} while requesting explanation for topic: {topic}")
        
        if 400 <= status_code < 500:
            raise LLMServiceException(f"Ошибка в запросе к сервису (код {status_code}). Пожалуйста, сообщите администратору.")
        else:
            raise LLMServiceException(f"Ошибка сервиса (код {status_code}). Попробуйте позже.")
    
    except Exception as e:
        logger.error(f"Error generating explanation for topic '{topic}': {e}")
        raise LLMServiceException(f"Произошла ошибка при генерации объяснения: {str(e)}")

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
    logging.basicConfig(level=logging.INFO)
    try:
        explanation = generate_explanation("Python programming")
        print(explanation)
    except LLMServiceException as e:
        print(f"Error: {e}")