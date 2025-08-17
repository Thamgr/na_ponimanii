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
    $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
    
    log "${GREEN}Virtual environment created and dependencies installed.${NC}"
fi

# Start services
log "${YELLOW}Starting services...${NC}"

# Start server
log "${YELLOW}Starting server...${NC}"
cd $PROJECT_DIR
nohup $VENV_DIR/bin/python $PROJECT_DIR/src/server/app.py > $PROJECT_DIR/logs/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > $PROJECT_DIR/logs/server.pid
log "${GREEN}Server started with PID $SERVER_PID${NC}"

# Wait for server to start
log "${YELLOW}Waiting for server to start...${NC}"
sleep 5

# Start bot
log "${YELLOW}Starting bot...${NC}"
cd $PROJECT_DIR
nohup $VENV_DIR/bin/python $PROJECT_DIR/src/bot/telegram_bot.py > $PROJECT_DIR/logs/bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > $PROJECT_DIR/logs/bot.pid
log "${GREEN}Bot started with PID $BOT_PID${NC}"

log "${GREEN}Services started successfully!${NC}"
log "${YELLOW}You can check the logs in:${NC}"
log "  $PROJECT_DIR/logs/server.log"
log "  $PROJECT_DIR/logs/bot.log"