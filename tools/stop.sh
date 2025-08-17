#!/bin/bash

# Define paths
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
SERVER_PID_FILE="$PROJECT_DIR/logs/server.pid"
BOT_PID_FILE="$PROJECT_DIR/logs/bot.pid"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Stop bot
if [ -f "$BOT_PID_FILE" ]; then
    BOT_PID=$(cat "$BOT_PID_FILE")
    kill $BOT_PID 2>/dev/null || true
    rm -f "$BOT_PID_FILE"
    echo "Bot stopped"
else
    BOT_PID=$(pgrep -f "python.*telegram_bot.py" || echo "")
    if [ -n "$BOT_PID" ]; then
        kill $BOT_PID
        echo "Bot stopped"
    fi
fi

# Stop server
if [ -f "$SERVER_PID_FILE" ]; then
    SERVER_PID=$(cat "$SERVER_PID_FILE")
    kill $SERVER_PID 2>/dev/null || true
    rm -f "$SERVER_PID_FILE"
    echo "Server stopped"
else
    SERVER_PID=$(pgrep -f "python.*app.py" || echo "")
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID
        echo "Server stopped"
    fi
fi

echo "Services stopped"