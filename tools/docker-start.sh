#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/env/.env"

# Check if env/.env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: env/.env file not found."
    echo "Please make sure the configuration file exists at env/.env"
    exit 1
fi

# Create data and logs directories if they don't exist
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

# Start the containers
echo "Starting Na Ponimanii services with Docker..."
cd "$PROJECT_DIR"
docker-compose up -d

echo "Services started successfully!"
echo "The API is available at http://localhost:8000"
echo "Use 'docker-compose logs -f' to view logs"