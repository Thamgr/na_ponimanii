#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
STOP_SCRIPT="$SCRIPT_DIR/stop.sh"
START_SCRIPT="$SCRIPT_DIR/start.sh"

# Make scripts executable
chmod +x "$STOP_SCRIPT"
chmod +x "$START_SCRIPT"

# Stop services
$STOP_SCRIPT

# Wait a moment
sleep 2

# Start services
$START_SCRIPT

echo "Restart completed"