#!/bin/bash

# Na Ponimanii Deployment Script
# This script deploys the Na Ponimanii bot and server as systemd services

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/na_ponimanii"
SYSTEMD_DIR="/etc/systemd/system"
BOT_SERVICE="na_ponimanii_bot.service"
SERVER_SERVICE="na_ponimanii_server.service"

# Create installation directory if it doesn't exist
log "${YELLOW}Creating installation directory...${NC}"
mkdir -p $INSTALL_DIR
chmod 755 $INSTALL_DIR

# Create directory structure
log "${YELLOW}Creating directory structure...${NC}"
mkdir -p $INSTALL_DIR/src/bot
mkdir -p $INSTALL_DIR/src/server
mkdir -p $INSTALL_DIR/env
mkdir -p $INSTALL_DIR/tools

# Copy project files to installation directory
log "${YELLOW}Copying project files...${NC}"
cp -r $PROJECT_DIR/src $INSTALL_DIR/
cp -r $PROJECT_DIR/env $INSTALL_DIR/
cp -r $PROJECT_DIR/tools $INSTALL_DIR/
cp $PROJECT_DIR/requirements.txt $INSTALL_DIR/
cp $PROJECT_DIR/README.md $INSTALL_DIR/ 2>/dev/null || true
cp $PROJECT_DIR/DEPLOYMENT.md $INSTALL_DIR/ 2>/dev/null || true
cp $PROJECT_DIR/.env $INSTALL_DIR/ 2>/dev/null || true
cp $PROJECT_DIR/.env.example $INSTALL_DIR/ 2>/dev/null || true

# Set correct permissions
log "${YELLOW}Setting file permissions...${NC}"
find $INSTALL_DIR -name "*.py" -exec chmod 644 {} \;
find $INSTALL_DIR -name "*.md" -exec chmod 644 {} \;
find $INSTALL_DIR -name "*.sh" -exec chmod 755 {} \;
chmod 644 $INSTALL_DIR/requirements.txt
chmod 644 $INSTALL_DIR/.env 2>/dev/null || true

# Install dependencies
log "${YELLOW}Installing dependencies...${NC}"
pip3 install -r $INSTALL_DIR/requirements.txt

# Create logs directory
log "${YELLOW}Creating logs directory...${NC}"
mkdir -p $INSTALL_DIR/logs
chmod 755 $INSTALL_DIR/logs

# Copy systemd service files
log "${YELLOW}Setting up systemd services...${NC}"
cp $INSTALL_DIR/tools/$BOT_SERVICE $SYSTEMD_DIR/
cp $INSTALL_DIR/tools/$SERVER_SERVICE $SYSTEMD_DIR/
chmod 644 $SYSTEMD_DIR/$BOT_SERVICE
chmod 644 $SYSTEMD_DIR/$SERVER_SERVICE

# Reload systemd
log "${YELLOW}Reloading systemd...${NC}"
systemctl daemon-reload

# Enable and start services
log "${YELLOW}Enabling and starting services...${NC}"
systemctl enable $SERVER_SERVICE
systemctl enable $BOT_SERVICE
systemctl start $SERVER_SERVICE
systemctl start $BOT_SERVICE

# Check service status
log "${YELLOW}Checking service status...${NC}"
systemctl status $SERVER_SERVICE --no-pager
systemctl status $BOT_SERVICE --no-pager

log "${GREEN}Deployment completed successfully!${NC}"
log "${YELLOW}You can check the logs with:${NC}"
log "  journalctl -u $SERVER_SERVICE -f"
log "  journalctl -u $BOT_SERVICE -f"