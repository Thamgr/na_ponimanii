#!/bin/bash

# Na Ponimanii Restart Script
# This script restarts the Na Ponimanii bot and server services

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

# Define services
BOT_SERVICE="na_ponimanii_bot.service"
SERVER_SERVICE="na_ponimanii_server.service"

# Check if services exist
if [ ! -f "/etc/systemd/system/$BOT_SERVICE" ] || [ ! -f "/etc/systemd/system/$SERVER_SERVICE" ]; then
    log "${RED}Services are not installed.${NC}"
    exit 1
fi

# Restart server service
log "${YELLOW}Restarting server service...${NC}"
systemctl restart $SERVER_SERVICE
log "${GREEN}Server service restarted.${NC}"

# Wait a moment for the server to start
log "${YELLOW}Waiting for server to start...${NC}"
sleep 5

# Restart bot service
log "${YELLOW}Restarting bot service...${NC}"
systemctl restart $BOT_SERVICE
log "${GREEN}Bot service restarted.${NC}"

# Check service status
log "${YELLOW}Checking service status...${NC}"
systemctl status $SERVER_SERVICE --no-pager
systemctl status $BOT_SERVICE --no-pager

log "${GREEN}Restart completed successfully!${NC}"