#!/bin/bash

# Na Ponimanii Stop Script
# This script stops the bot and server

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Define paths
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
SERVER_PID_FILE="$PROJECT_DIR/logs/server.pid"
BOT_PID_FILE="$PROJECT_DIR/logs/bot.pid"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Stop bot
log "${YELLOW}Stopping bot...${NC}"
if [ -f "$BOT_PID_FILE" ]; then
    BOT_PID=$(cat "$BOT_PID_FILE")
    if ps -p $BOT_PID > /dev/null; then
        kill $BOT_PID
        log "${GREEN}Bot stopped (PID: $BOT_PID)${NC}"
    else
        log "${YELLOW}Bot process not found (PID: $BOT_PID)${NC}"
    fi
    rm -f "$BOT_PID_FILE"
else
    log "${YELLOW}Bot PID file not found, trying to find process...${NC}"
    BOT_PID=$(pgrep -f "python.*telegram_bot.py" || echo "")
    if [ -n "$BOT_PID" ]; then
        kill $BOT_PID
        log "${GREEN}Bot stopped (PID: $BOT_PID)${NC}"
    else
        log "${YELLOW}No running bot process found${NC}"
    fi
fi

# Stop server
log "${YELLOW}Stopping server...${NC}"
if [ -f "$SERVER_PID_FILE" ]; then
    SERVER_PID=$(cat "$SERVER_PID_FILE")
    if ps -p $SERVER_PID > /dev/null; then
        kill $SERVER_PID
        log "${GREEN}Server stopped (PID: $SERVER_PID)${NC}"
    else
        log "${YELLOW}Server process not found (PID: $SERVER_PID)${NC}"
    fi
    rm -f "$SERVER_PID_FILE"
else
    log "${YELLOW}Server PID file not found, trying to find process...${NC}"
    SERVER_PID=$(pgrep -f "python.*app.py" || echo "")
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID
        log "${GREEN}Server stopped (PID: $SERVER_PID)${NC}"
    else
        log "${YELLOW}No running server process found${NC}"
    fi
fi

log "${GREEN}Services stopped successfully!${NC}"