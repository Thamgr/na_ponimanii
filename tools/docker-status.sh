#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVER_LOG_FILE="$PROJECT_DIR/logs/server.log"
BOT_LOG_FILE="$PROJECT_DIR/logs/bot.log"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Check Docker container status
echo "Checking Docker container status..."
cd "$PROJECT_DIR"

# Get container status
CONTAINER_STATUS=$(docker-compose ps --services | grep -q "app" && echo "running" || echo "stopped")

if [ "$CONTAINER_STATUS" == "running" ]; then
    echo "Na Ponimanii container is running"
    
    # Show container details
    echo -e "\nContainer details:"
    docker-compose ps
    
    # Show container logs (last 10 lines)
    echo -e "\nRecent container logs (last 10 lines):"
    docker-compose logs --tail=10
else
    echo "Na Ponimanii container is not running"
fi

# Print log file information
echo -e "\nLog Files:"
echo "  Server Log: $SERVER_LOG_FILE"
echo "  Bot Log: $BOT_LOG_FILE"

# Print Docker commands help
echo -e "\nUseful Docker commands:"
echo "  View logs: docker-compose logs -f"
echo "  Restart services: tools/docker-stop.sh && tools/docker-start.sh"
echo "  Update application: tools/docker-update.sh"