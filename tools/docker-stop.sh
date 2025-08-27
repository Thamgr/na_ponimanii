#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Stopping Na Ponimanii services..."
cd "$PROJECT_DIR"
docker-compose down

echo "Services stopped successfully!"