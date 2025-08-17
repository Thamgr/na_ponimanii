#!/bin/bash

# Na Ponimanii Status Script
# This script checks the status of the Na Ponimanii bot and server services

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

# Define services
BOT_SERVICE="na_ponimanii_bot.service"
SERVER_SERVICE="na_ponimanii_server.service"

# Print header
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${BLUE}   Na Ponimanii Services Status Check   ${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Check if services exist
if [ ! -f "/etc/systemd/system/$BOT_SERVICE" ] || [ ! -f "/etc/systemd/system/$SERVER_SERVICE" ]; then
    log "${RED}Services are not installed.${NC}"
    exit 1
fi

# Check server service status
log "${YELLOW}Checking server status...${NC}"
if systemctl is-active --quiet $SERVER_SERVICE; then
    log "${GREEN}Server service is running.${NC}"
else
    log "${RED}Server service is not running.${NC}"
fi

# Check bot service status
log "${YELLOW}Checking bot status...${NC}"
if systemctl is-active --quiet $BOT_SERVICE; then
    log "${GREEN}Bot service is running.${NC}"
else
    log "${RED}Bot service is not running.${NC}"
fi

# Print detailed status
echo -e "\n${YELLOW}Detailed Server Status:${NC}"
systemctl status $SERVER_SERVICE --no-pager

echo -e "\n${YELLOW}Detailed Bot Status:${NC}"
systemctl status $BOT_SERVICE --no-pager

# Print log instructions
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${YELLOW}To view logs, run:${NC}"
echo -e "  journalctl -u $SERVER_SERVICE -f"
echo -e "  journalctl -u $BOT_SERVICE -f"
echo -e "${BLUE}=======================================${NC}\n"