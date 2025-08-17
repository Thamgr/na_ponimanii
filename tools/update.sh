#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"
STOP_SCRIPT="$SCRIPT_DIR/stop.sh"
START_SCRIPT="$SCRIPT_DIR/start.sh"
GITHUB_REPO="https://github.com/yourusername/na_ponimanii.git"  # Replace with your actual repo URL
BRANCH="main"  # Replace with your branch name if different

# Make scripts executable
chmod +x "$STOP_SCRIPT"
chmod +x "$START_SCRIPT"

# Stop services
$STOP_SCRIPT

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Pull latest changes
cd $PROJECT_DIR
if [ -d "$PROJECT_DIR/.git" ]; then
    git pull origin $BRANCH
else
    TEMP_DIR="/tmp/na_ponimanii_update"
    rm -rf $TEMP_DIR
    git clone --branch $BRANCH $GITHUB_REPO $TEMP_DIR
    rsync -av --exclude='.git' --exclude='logs' --exclude='venv' --exclude='env/.env' $TEMP_DIR/ $PROJECT_DIR/
    rm -rf $TEMP_DIR
fi

# Make sure env directory exists
mkdir -p "$PROJECT_DIR/env"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi

# Update dependencies
$VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
$VENV_DIR/bin/pip install httpx python-telegram-bot fastapi uvicorn

# Start services
$START_SCRIPT

echo "Update completed"