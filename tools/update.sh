#!/bin/bash

# Na Ponimanii Update Script
# This script pulls the latest updates from GitHub and restarts the services

# Exit on any error
set -e

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"
STOP_SCRIPT="$SCRIPT_DIR/stop.sh"
START_SCRIPT="$SCRIPT_DIR/start.sh"
GITHUB_REPO="https://github.com/yourusername/na_ponimanii.git"  # Replace with your actual repo URL
BRANCH="main"  # Replace with your branch name if different

# Check if scripts exist
if [ ! -f "$STOP_SCRIPT" ] || [ ! -f "$START_SCRIPT" ]; then
    log "${RED}Stop or start script not found. Please make sure they exist.${NC}"
    exit 1
fi

# Make scripts executable
chmod +x "$STOP_SCRIPT"
chmod +x "$START_SCRIPT"

# Print header
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${BLUE}   Na Ponimanii Update Process   ${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Stop services
log "${YELLOW}Stopping services...${NC}"
$STOP_SCRIPT

# Check if .env file exists
if [ -f "$PROJECT_DIR/env/.env" ]; then
    log "${YELLOW}Found .env file, will preserve it during update...${NC}"
fi

# Pull latest changes
log "${YELLOW}Pulling latest changes from GitHub...${NC}"
cd $PROJECT_DIR
if [ -d "$PROJECT_DIR/.git" ]; then
    # If it's a git repository, pull the latest changes
    git pull origin $BRANCH
else
    # If it's not a git repository, clone the repository to a temporary directory and copy the files
    log "${YELLOW}Not a git repository. Cloning to temporary directory...${NC}"
    TEMP_DIR="/tmp/na_ponimanii_update"
    rm -rf $TEMP_DIR
    git clone --branch $BRANCH $GITHUB_REPO $TEMP_DIR
    
    # Copy files from temporary directory
    log "${YELLOW}Copying files from temporary directory...${NC}"
    rsync -av --exclude='.git' --exclude='logs' --exclude='venv' --exclude='env/.env' --exclude='env/.env.*' $TEMP_DIR/ $PROJECT_DIR/
    
    # Make sure env directory exists
    mkdir -p "$PROJECT_DIR/env"
    
    # Clean up
    rm -rf $TEMP_DIR
fi

# Make sure the env directory exists
mkdir -p "$PROJECT_DIR/env"

# Check if .env file exists after update
if [ ! -f "$PROJECT_DIR/env/.env" ]; then
    log "${YELLOW}No .env file found after update. Creating from .env.example if available...${NC}"
    if [ -f "$PROJECT_DIR/env/.env.example" ]; then
        cp "$PROJECT_DIR/env/.env.example" "$PROJECT_DIR/env/.env"
        log "${YELLOW}Created .env file from .env.example. Please update it with your configuration.${NC}"
    else
        log "${RED}No .env.example file found. You will need to create a .env file manually.${NC}"
        touch "$PROJECT_DIR/env/.env"
    fi
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    log "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log "${YELLOW}Using Python version: $PYTHON_VERSION${NC}"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    log "${RED}pip3 is not installed. Please install pip3 and try again.${NC}"
    exit 1
fi

# Update dependencies in virtual environment
if [ -d "$VENV_DIR" ]; then
    log "${YELLOW}Updating dependencies in existing virtual environment...${NC}"
    
    # Check if virtual environment is valid
    if [ ! -f "$VENV_DIR/bin/python" ]; then
        log "${RED}Virtual environment appears to be corrupted. Recreating...${NC}"
        rm -rf $VENV_DIR
        
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
    fi
    
    # Update dependencies
    $VENV_DIR/bin/pip install --upgrade pip
    $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
    
    # Install specific packages explicitly
    log "${YELLOW}Installing required packages explicitly...${NC}"
    $VENV_DIR/bin/pip install httpx python-telegram-bot fastapi uvicorn python-dotenv sqlalchemy
else
    log "${YELLOW}Creating virtual environment...${NC}"
    
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
    
    # Install dependencies
    $VENV_DIR/bin/pip install --upgrade pip
    $VENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt
    
    # Install specific packages explicitly
    log "${YELLOW}Installing required packages explicitly...${NC}"
    $VENV_DIR/bin/pip install httpx python-telegram-bot fastapi uvicorn python-dotenv sqlalchemy
fi

log "${GREEN}Dependencies updated successfully.${NC}"

# Check if Python modules can be imported
log "${YELLOW}Testing Python imports...${NC}"

# Test httpx import
if $VENV_DIR/bin/python -c "import httpx" 2>/dev/null; then
    HTTPX_VERSION=$($VENV_DIR/bin/python -c "import httpx; print(httpx.__version__)" 2>/dev/null)
    log "${GREEN}httpx is installed (version: $HTTPX_VERSION)${NC}"
else
    log "${RED}Failed to import httpx. Installing...${NC}"
    $VENV_DIR/bin/pip install httpx
fi

# Test fastapi import
if $VENV_DIR/bin/python -c "import fastapi" 2>/dev/null; then
    FASTAPI_VERSION=$($VENV_DIR/bin/python -c "import fastapi; print(fastapi.__version__)" 2>/dev/null)
    log "${GREEN}fastapi is installed (version: $FASTAPI_VERSION)${NC}"
else
    log "${RED}Failed to import fastapi. Installing...${NC}"
    $VENV_DIR/bin/pip install fastapi
fi

# Test telegram import
if $VENV_DIR/bin/python -c "import telegram" 2>/dev/null; then
    TELEGRAM_VERSION=$($VENV_DIR/bin/python -c "import telegram; print(telegram.__version__)" 2>/dev/null)
    log "${GREEN}telegram is installed (version: $TELEGRAM_VERSION)${NC}"
else
    log "${RED}Failed to import telegram. Installing...${NC}"
    $VENV_DIR/bin/pip install python-telegram-bot
fi

log "${GREEN}Dependencies updated successfully.${NC}"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Start services
log "${YELLOW}Starting services...${NC}"
$START_SCRIPT

log "${GREEN}Update completed successfully!${NC}"