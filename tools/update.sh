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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Define paths
INSTALL_DIR="/opt/na_ponimanii"
TEMP_DIR="/tmp/na_ponimanii_update"
GITHUB_REPO="https://github.com/yourusername/na_ponimanii.git"  # Replace with your actual repo URL
BRANCH="main"  # Replace with your branch name if different

# Define services
BOT_SERVICE="na_ponimanii_bot.service"
SERVER_SERVICE="na_ponimanii_server.service"

# Check if services exist
if [ ! -f "/etc/systemd/system/$BOT_SERVICE" ] || [ ! -f "/etc/systemd/system/$SERVER_SERVICE" ]; then
    log "${RED}Services are not installed. Please run deploy.sh first.${NC}"
    exit 1
fi

# Print header
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${BLUE}   Na Ponimanii Update Process   ${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Create temp directory
log "${YELLOW}Creating temporary directory...${NC}"
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

# Clone the repository
log "${YELLOW}Cloning the latest version from GitHub...${NC}"
git clone --branch $BRANCH $GITHUB_REPO $TEMP_DIR

# Check if .env file exists in the installation directory
if [ -f "$INSTALL_DIR/.env" ]; then
    log "${YELLOW}Preserving existing .env file...${NC}"
    cp $INSTALL_DIR/.env $TEMP_DIR/
else
    log "${RED}Warning: No .env file found in installation directory.${NC}"
    if [ -f "$TEMP_DIR/.env.example" ]; then
        log "${YELLOW}Copying .env.example to .env...${NC}"
        cp $TEMP_DIR/.env.example $TEMP_DIR/.env
        log "${RED}Please update the .env file with your configuration.${NC}"
    else
        log "${RED}No .env.example file found. You will need to create a .env file manually.${NC}"
    fi
fi

# Stop services
log "${YELLOW}Stopping services...${NC}"
systemctl stop $BOT_SERVICE
systemctl stop $SERVER_SERVICE

# Backup the current installation
log "${YELLOW}Backing up current installation...${NC}"
BACKUP_DIR="$INSTALL_DIR.backup.$(date +%Y%m%d%H%M%S)"
cp -r $INSTALL_DIR $BACKUP_DIR
log "${GREEN}Backup created at $BACKUP_DIR${NC}"

# Copy new files to installation directory
log "${YELLOW}Updating files...${NC}"
rsync -av --exclude='.git' --exclude='logs' $TEMP_DIR/ $INSTALL_DIR/

# Ensure logs directory exists
log "${YELLOW}Ensuring logs directory exists...${NC}"
mkdir -p $INSTALL_DIR/logs

# Set correct permissions
log "${YELLOW}Setting permissions...${NC}"
find $INSTALL_DIR -name "*.py" -exec chmod 644 {} \;
find $INSTALL_DIR -name "*.md" -exec chmod 644 {} \;
find $INSTALL_DIR -name "*.sh" -exec chmod 755 {} \;
chmod 644 $INSTALL_DIR/requirements.txt
chmod 644 $INSTALL_DIR/.env 2>/dev/null || true

# Ensure directory structure exists
log "${YELLOW}Ensuring directory structure...${NC}"
mkdir -p $INSTALL_DIR/src/bot
mkdir -p $INSTALL_DIR/src/server
mkdir -p $INSTALL_DIR/env
mkdir -p $INSTALL_DIR/tools

# Update dependencies
log "${YELLOW}Updating dependencies...${NC}"
pip3 install -r $INSTALL_DIR/requirements.txt

# Start services
log "${YELLOW}Starting services...${NC}"
systemctl start $SERVER_SERVICE
sleep 5  # Wait for server to start
systemctl start $BOT_SERVICE

# Check service status
log "${YELLOW}Checking service status...${NC}"
systemctl status $SERVER_SERVICE --no-pager
systemctl status $BOT_SERVICE --no-pager

# Clean up
log "${YELLOW}Cleaning up...${NC}"
rm -rf $TEMP_DIR

log "${GREEN}Update completed successfully!${NC}"
log "${YELLOW}If you encounter any issues, you can restore the backup from $BACKUP_DIR${NC}"