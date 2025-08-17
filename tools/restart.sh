#!/bin/bash

# Na Ponimanii Restart Script
# This script restarts the bot and server

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
STOP_SCRIPT="$SCRIPT_DIR/stop.sh"
START_SCRIPT="$SCRIPT_DIR/start.sh"

# Check if scripts exist
if [ ! -f "$STOP_SCRIPT" ] || [ ! -f "$START_SCRIPT" ]; then
    log "${RED}Stop or start script not found. Please make sure they exist.${NC}"
    exit 1
fi

# Make scripts executable
chmod +x "$STOP_SCRIPT"
chmod +x "$START_SCRIPT"

# Print header
echo -e "\n${YELLOW}=======================================${NC}"
echo -e "${YELLOW}   Na Ponimanii Restart Process   ${NC}"
echo -e "${YELLOW}=======================================${NC}\n"

# Stop services
log "${YELLOW}Stopping services...${NC}"
$STOP_SCRIPT

# Wait a moment
log "${YELLOW}Waiting for services to stop completely...${NC}"
sleep 3

# Start services
log "${YELLOW}Starting services...${NC}"
$START_SCRIPT

log "${GREEN}Restart completed successfully!${NC}"