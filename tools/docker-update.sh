#!/bin/bash
set -euo pipefail

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
STOP_SCRIPT="$SCRIPT_DIR/docker-stop.sh"
START_SCRIPT="$SCRIPT_DIR/docker-start.sh"
GITHUB_REPO="https://github.com/yourusername/na_ponimanii.git"  # Replace with your actual repo URL

# Make scripts executable
chmod +x "$STOP_SCRIPT"
chmod +x "$START_SCRIPT"

# Create logs and data directories
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/env"

# Pull latest changes
cd "$PROJECT_DIR"
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "Pulling latest changes from git..."
    git pull origin
else
    echo "Cloning repository..."
    TEMP_DIR="/tmp/na_ponimanii_update"
    rm -rf "$TEMP_DIR"
    git clone "$GITHUB_REPO" "$TEMP_DIR"
    rsync -av --exclude='.git' --exclude='logs' --exclude='data' --exclude='env/.env' "$TEMP_DIR/" "$PROJECT_DIR/"
    rm -rf "$TEMP_DIR"
fi

# Rebuild Docker image with BuildKit
echo "Rebuilding Docker image with BuildKit..."
cd "$PROJECT_DIR"
DOCKER_BUILDKIT=1 docker-compose build --no-cache
echo "Docker image rebuilt successfully."

# Stop services (only now, чтобы не было простоя на время билда)
echo "Stopping services..."
$STOP_SCRIPT

# Start services
echo "Starting services..."
$START_SCRIPT

echo "Update completed"
