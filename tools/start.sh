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

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    log "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv $VENV_DIR
    
    log "${YELLOW}Installing dependencies...${NC}"
    $VENV_DIR/bin/pip install --upgrade pip
    $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
    
    # Install specific packages explicitly
    log "${YELLOW}Installing required packages explicitly...${NC}"
    $VENV_DIR/bin/pip install httpx python-telegram-bot fastapi uvicorn python-dotenv sqlalchemy langchain langchain-core langchain-openai
    
    log "${GREEN}Virtual environment created and dependencies installed.${NC}"
else
    # Update dependencies in case requirements.txt has changed
    log "${YELLOW}Updating dependencies...${NC}"
    $VENV_DIR/bin/pip install --upgrade pip
    $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
    
    # Install specific packages explicitly
    log "${YELLOW}Installing required packages explicitly...${NC}"
    $VENV_DIR/bin/pip install httpx python-telegram-bot fastapi uvicorn python-dotenv sqlalchemy langchain langchain-core langchain-openai
    
    log "${GREEN}Dependencies updated.${NC}"
fi

# Verify httpx is installed and show version
log "${YELLOW}Checking installed packages...${NC}"
$VENV_DIR/bin/pip list | grep httpx || echo "httpx not found!"
$VENV_DIR/bin/pip list | grep telegram || echo "python-telegram-bot not found!"
$VENV_DIR/bin/pip list | grep fastapi || echo "fastapi not found!"

# Create logs directory if it doesn't exist
log "${YELLOW}Creating logs directory...${NC}"
mkdir -p "$PROJECT_DIR/logs"

# Start services
log "${YELLOW}Starting services...${NC}"

# Check if Python modules can be imported
log "${YELLOW}Testing Python imports...${NC}"
$VENV_DIR/bin/python -c "import httpx; print('httpx version:', httpx.__version__)" || log "${RED}Failed to import httpx${NC}"
$VENV_DIR/bin/python -c "import fastapi; print('fastapi version:', fastapi.__version__)" || log "${RED}Failed to import fastapi${NC}"
$VENV_DIR/bin/python -c "import telegram; print('telegram version:', telegram.__version__)" || log "${RED}Failed to import telegram${NC}"

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