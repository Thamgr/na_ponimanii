#!/bin/bash

# Na Ponimanii Status Script
# This script checks the status of the Na Ponimanii bot and server processes

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Define paths
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
SERVER_PID_FILE="$PROJECT_DIR/logs/server.pid"
BOT_PID_FILE="$PROJECT_DIR/logs/bot.pid"
SERVER_LOG_FILE="$PROJECT_DIR/logs/server.log"
BOT_LOG_FILE="$PROJECT_DIR/logs/bot.log"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Print header
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${BLUE}   Na Ponimanii Services Status Check   ${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Check server status
log "${YELLOW}Checking server status...${NC}"
if [ -f "$SERVER_PID_FILE" ]; then
    SERVER_PID=$(cat "$SERVER_PID_FILE")
    if ps -p $SERVER_PID > /dev/null; then
        log "${GREEN}Server is running (PID: $SERVER_PID)${NC}"
    else
        log "${RED}Server process not found (PID: $SERVER_PID)${NC}"
    fi
else
    log "${RED}Server PID file not found${NC}"
    SERVER_PID=$(pgrep -f "python.*app.py" || echo "")
    if [ -n "$SERVER_PID" ]; then
        log "${GREEN}Server is running (PID: $SERVER_PID)${NC}"
    else
        log "${RED}No running server process found${NC}"
    fi
fi

# Check bot status
log "${YELLOW}Checking bot status...${NC}"
if [ -f "$BOT_PID_FILE" ]; then
    BOT_PID=$(cat "$BOT_PID_FILE")
    if ps -p $BOT_PID > /dev/null; then
        log "${GREEN}Bot is running (PID: $BOT_PID)${NC}"
    else
        log "${RED}Bot process not found (PID: $BOT_PID)${NC}"
    fi
else
    log "${RED}Bot PID file not found${NC}"
    BOT_PID=$(pgrep -f "python.*telegram_bot.py" || echo "")
    if [ -n "$BOT_PID" ]; then
        log "${GREEN}Bot is running (PID: $BOT_PID)${NC}"
    else
        log "${RED}No running bot process found${NC}"
    fi
fi

# Print log file information
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${YELLOW}Log Files:${NC}"
echo -e "  Server Log: $SERVER_LOG_FILE"
echo -e "  Bot Log: $BOT_LOG_FILE"
echo -e ""
echo -e "${YELLOW}To view logs, run:${NC}"
echo -e "  tail -f $SERVER_LOG_FILE"
echo -e "  tail -f $BOT_LOG_FILE"
echo -e "${BLUE}=======================================${NC}\n"

# Print recent log entries if available
if [ -f "$SERVER_LOG_FILE" ]; then
    echo -e "${YELLOW}Recent server log entries:${NC}"
    tail -n 5 "$SERVER_LOG_FILE"
    echo -e ""
fi

if [ -f "$BOT_LOG_FILE" ]; then
    echo -e "${YELLOW}Recent bot log entries:${NC}"
    tail -n 5 "$BOT_LOG_FILE"
    echo -e ""
fi