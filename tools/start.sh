#!/bin/bash

# Define paths
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
    $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
    $VENV_DIR/bin/pip install httpx python-telegram-bot fastapi uvicorn
fi

# Start server
cd $PROJECT_DIR
nohup $VENV_DIR/bin/python $PROJECT_DIR/src/server/app.py > $PROJECT_DIR/logs/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > $PROJECT_DIR/logs/server.pid
echo "Server started with PID $SERVER_PID"

# Wait for server to start
sleep 3

# Start bot
cd $PROJECT_DIR
nohup $VENV_DIR/bin/python $PROJECT_DIR/src/bot/telegram_bot.py > $PROJECT_DIR/logs/bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > $PROJECT_DIR/logs/bot.pid
echo "Bot started with PID $BOT_PID"

echo "Services started successfully"