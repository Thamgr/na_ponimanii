#!/bin/bash

# Na Ponimanii Start Script
# This script starts the bot and server

# Exit on any error
set -e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Define paths
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
BOT_SERVICE="na_ponimanii_bot.service"
SERVER_SERVICE="na_ponimanii_server.service"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    log "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log "${YELLOW}Using Python version: $PYTHON_VERSION${NC}"

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    log "${RED}pip3 is not installed. Please install pip3 and try again.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    log "${YELLOW}Creating Python virtual environment...${NC}"
    
    # Check if venv module is available
    if ! python3 -c "import venv" &> /dev/null; then
        log "${RED}Python venv module is not available. Installing python3-venv...${NC}"
        apt-get update && apt-get install -y python3-venv
    fi
    
    # Create virtual environment
    python3 -m venv $VENV_DIR
    
    # Check if virtual environment was created successfully
    if [ ! -f "$VENV_DIR/bin/python" ]; then
        log "${RED}Failed to create virtual environment. Please check your Python installation.${NC}"
        exit 1
    fi
    
    log "${GREEN}Virtual environment created successfully.${NC}"
    
    # Install dependencies
    log "${YELLOW}Installing dependencies...${NC}"
    $VENV_DIR/bin/pip3 install --upgrade pip
    $VENV_DIR/bin/pip3 install -r $PROJECT_DIR/requirements.txt
    
    # Install specific packages explicitly
    log "${YELLOW}Installing required packages explicitly...${NC}"
    $VENV_DIR/bin/pip3 install httpx python-telegram-bot fastapi uvicorn python-dotenv sqlalchemy
    
    log "${GREEN}Dependencies installed.${NC}"
else
    # Update dependencies in case requirements.txt has changed
    log "${YELLOW}Updating dependencies...${NC}"
    $VENV_DIR/bin/pip3 install --upgrade pip
    $VENV_DIR/bin/pip3 install -r $PROJECT_DIR/requirements.txt
    
    # Install specific packages explicitly
    log "${YELLOW}Installing required packages explicitly...${NC}"
    $VENV_DIR/bin/pip3 install httpx python-telegram-bot fastapi uvicorn python-dotenv sqlalchemy
    
    log "${GREEN}Dependencies updated.${NC}"
fi

# Verify httpx is installed and show version
log "${YELLOW}Checking installed packages...${NC}"
$VENV_DIR/bin/pip3 list | grep httpx || echo "httpx not found!"
$VENV_DIR/bin/pip3 list | grep telegram || echo "python-telegram-bot not found!"
$VENV_DIR/bin/pip3 list | grep fastapi || echo "fastapi not found!"

# Create logs directory if it doesn't exist
log "${YELLOW}Creating logs directory...${NC}"
mkdir -p "$PROJECT_DIR/logs"

# Start services
log "${YELLOW}Starting services...${NC}"

# Check if Python modules can be imported
log "${YELLOW}Testing Python imports...${NC}"

# Test httpx import
if $VENV_DIR/bin/python -c "import httpx" 2>/dev/null; then
    HTTPX_VERSION=$($VENV_DIR/bin/python -c "import httpx; print(httpx.__version__)" 2>/dev/null)
    log "${GREEN}httpx is installed (version: $HTTPX_VERSION)${NC}"
else
    log "${RED}Failed to import httpx. Installing...${NC}"
    $VENV_DIR/bin/pip3 install httpx
fi

# Test fastapi import
if $VENV_DIR/bin/python -c "import fastapi" 2>/dev/null; then
    FASTAPI_VERSION=$($VENV_DIR/bin/python -c "import fastapi; print(fastapi.__version__)" 2>/dev/null)
    log "${GREEN}fastapi is installed (version: $FASTAPI_VERSION)${NC}"
else
    log "${RED}Failed to import fastapi. Installing...${NC}"
    $VENV_DIR/bin/pip3 install fastapi
fi

# Test telegram import
if $VENV_DIR/bin/python -c "import telegram" 2>/dev/null; then
    TELEGRAM_VERSION=$($VENV_DIR/bin/python -c "import telegram; print(telegram.__version__)" 2>/dev/null)
    log "${GREEN}telegram is installed (version: $TELEGRAM_VERSION)${NC}"
else
    log "${RED}Failed to import telegram. Installing...${NC}"
    $VENV_DIR/bin/pip3 install python-telegram-bot
fi

# Start server
log "${YELLOW}Starting server...${NC}"
cd $PROJECT_DIR
log "${YELLOW}Running: $VENV_DIR/bin/python $PROJECT_DIR/src/server/app.py${NC}"
nohup $VENV_DIR/bin/python $PROJECT_DIR/src/server/app.py > $PROJECT_DIR/logs/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > $PROJECT_DIR/logs/server.pid
log "${GREEN}Server started with PID $SERVER_PID${NC}"

# Wait for server to start
log "${YELLOW}Waiting for server to start...${NC}"
sleep 5

# Check if server is still running
if ps -p $SERVER_PID > /dev/null; then
    log "${GREEN}Server is running (PID: $SERVER_PID)${NC}"
    log "${YELLOW}Server log tail:${NC}"
    tail -n 5 $PROJECT_DIR/logs/server.log
else
    log "${RED}Server failed to start!${NC}"
    log "${YELLOW}Server log tail:${NC}"
    tail -n 20 $PROJECT_DIR/logs/server.log
    exit 1
fi

# Start bot
log "${YELLOW}Starting bot...${NC}"
cd $PROJECT_DIR
log "${YELLOW}Running: $VENV_DIR/bin/python $PROJECT_DIR/src/bot/telegram_bot.py${NC}"
nohup $VENV_DIR/bin/python $PROJECT_DIR/src/bot/telegram_bot.py > $PROJECT_DIR/logs/bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > $PROJECT_DIR/logs/bot.pid
log "${GREEN}Bot started with PID $BOT_PID${NC}"

# Check if bot is still running
sleep 2
if ps -p $BOT_PID > /dev/null; then
    log "${GREEN}Bot is running (PID: $BOT_PID)${NC}"
    log "${YELLOW}Bot log tail:${NC}"
    tail -n 5 $PROJECT_DIR/logs/bot.log
else
    log "${RED}Bot failed to start!${NC}"
    log "${YELLOW}Bot log tail:${NC}"
    tail -n 20 $PROJECT_DIR/logs/bot.log
    exit 1
fi

log "${GREEN}Services started successfully!${NC}"
log "${YELLOW}You can check the logs in:${NC}"
log "  $PROJECT_DIR/logs/server.log"
log "  $PROJECT_DIR/logs/bot.log"