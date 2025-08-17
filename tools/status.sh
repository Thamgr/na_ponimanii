#!/bin/bash

# Define paths
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
SERVER_PID_FILE="$PROJECT_DIR/logs/server.pid"
BOT_PID_FILE="$PROJECT_DIR/logs/bot.pid"
SERVER_LOG_FILE="$PROJECT_DIR/logs/server.log"
BOT_LOG_FILE="$PROJECT_DIR/logs/bot.log"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Check server status
echo "Checking server status..."
if [ -f "$SERVER_PID_FILE" ]; then
    SERVER_PID=$(cat "$SERVER_PID_FILE")
    if ps -p $SERVER_PID > /dev/null; then
        echo "Server is running (PID: $SERVER_PID)"
    else
        echo "Server process not found (PID: $SERVER_PID)"
    fi
else
    SERVER_PID=$(pgrep -f "python.*app.py" || echo "")
    if [ -n "$SERVER_PID" ]; then
        echo "Server is running (PID: $SERVER_PID)"
    else
        echo "No running server process found"
    fi
fi

# Check bot status
echo "Checking bot status..."
if [ -f "$BOT_PID_FILE" ]; then
    BOT_PID=$(cat "$BOT_PID_FILE")
    if ps -p $BOT_PID > /dev/null; then
        echo "Bot is running (PID: $BOT_PID)"
    else
        echo "Bot process not found (PID: $BOT_PID)"
    fi
else
    BOT_PID=$(pgrep -f "python.*telegram_bot.py" || echo "")
    if [ -n "$BOT_PID" ]; then
        echo "Bot is running (PID: $BOT_PID)"
    else
        echo "No running bot process found"
    fi
fi

# Print log file information
echo "Log Files:"
echo "  Server Log: $SERVER_LOG_FILE"
echo "  Bot Log: $BOT_LOG_FILE"