#!/bin/bash

# Na Ponimanii Uninstall Script
# This script removes the Na Ponimanii bot and server systemd services

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
INSTALL_DIR="/opt/na_ponimanii"
SYSTEMD_DIR="/etc/systemd/system"
BOT_SERVICE="na_ponimanii_bot.service"
SERVER_SERVICE="na_ponimanii_server.service"

# Stop services if running
log "${YELLOW}Stopping services...${NC}"
systemctl stop $BOT_SERVICE 2>/dev/null || true
systemctl stop $SERVER_SERVICE 2>/dev/null || true

# Disable services
log "${YELLOW}Disabling services...${NC}"
systemctl disable $BOT_SERVICE 2>/dev/null || true
systemctl disable $SERVER_SERVICE 2>/dev/null || true

# Remove service files
log "${YELLOW}Removing service files...${NC}"
rm -f $SYSTEMD_DIR/$BOT_SERVICE
rm -f $SYSTEMD_DIR/$SERVER_SERVICE

# Reload systemd
log "${YELLOW}Reloading systemd...${NC}"
systemctl daemon-reload

# Ask if user wants to remove installation directory
read -p "Do you want to remove the installation directory ($INSTALL_DIR)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "${YELLOW}Removing installation directory...${NC}"
    rm -rf $INSTALL_DIR
    log "${GREEN}Installation directory removed.${NC}"
else
    log "${YELLOW}Installation directory kept.${NC}"
fi

log "${GREEN}Uninstallation completed successfully!${NC}"