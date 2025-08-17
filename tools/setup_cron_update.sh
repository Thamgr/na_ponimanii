#!/bin/bash

# Na Ponimanii Cron Setup Script
# This script sets up a cron job to automatically update the application

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
UPDATE_SCRIPT="$INSTALL_DIR/update.sh"
CRON_FILE="/etc/cron.d/na_ponimanii_update"
LOG_FILE="$INSTALL_DIR/logs/update_cron.log"

# Check if update script exists
if [ ! -f "$UPDATE_SCRIPT" ]; then
    log "${RED}Update script not found at $UPDATE_SCRIPT${NC}"
    log "${YELLOW}Please run deploy.sh first or make sure update.sh is in the correct location.${NC}"
    exit 1
fi

# Print header
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${BLUE}   Na Ponimanii Cron Job Setup   ${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Ask for schedule
echo -e "${YELLOW}Please select when to run automatic updates:${NC}"
echo "1) Daily at midnight"
echo "2) Weekly on Sunday at midnight"
echo "3) Monthly on the 1st at midnight"
echo "4) Custom schedule"
read -p "Enter your choice [1-4]: " choice

case $choice in
    1)
        # Daily at midnight
        SCHEDULE="0 0 * * *"
        DESCRIPTION="daily at midnight"
        ;;
    2)
        # Weekly on Sunday at midnight
        SCHEDULE="0 0 * * 0"
        DESCRIPTION="weekly on Sunday at midnight"
        ;;
    3)
        # Monthly on the 1st at midnight
        SCHEDULE="0 0 1 * *"
        DESCRIPTION="monthly on the 1st at midnight"
        ;;
    4)
        # Custom schedule
        echo -e "${YELLOW}Enter a custom cron schedule (e.g., '0 4 * * *' for daily at 4 AM):${NC}"
        read -p "Cron schedule: " SCHEDULE
        DESCRIPTION="on custom schedule: $SCHEDULE"
        ;;
    *)
        log "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

# Create cron job
log "${YELLOW}Creating cron job...${NC}"
cat > $CRON_FILE << EOF
# Na Ponimanii automatic update cron job
# Created on $(date)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Run update script $DESCRIPTION
$SCHEDULE root $UPDATE_SCRIPT >> $LOG_FILE 2>&1
EOF

# Set permissions
chmod 644 $CRON_FILE

# Create log file if it doesn't exist
mkdir -p $(dirname $LOG_FILE)
touch $LOG_FILE
chmod 644 $LOG_FILE

log "${GREEN}Cron job set up successfully!${NC}"
log "${YELLOW}The application will be updated $DESCRIPTION${NC}"
log "${YELLOW}Update logs will be written to $LOG_FILE${NC}"

# Show how to remove the cron job
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${YELLOW}To remove the automatic updates, run:${NC}"
echo -e "  sudo rm $CRON_FILE"
echo -e "${BLUE}=======================================${NC}\n"