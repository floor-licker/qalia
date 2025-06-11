#!/bin/bash

# Docker Cleanup Script for QA AI Testing
# Cleans up Docker space before running act

echo "🧹 Cleaning up Docker space for QA AI testing..."

# Stop all running containers
echo "Stopping containers..."
docker stop $(docker ps -q) 2>/dev/null || echo "No containers to stop"

# Remove stopped containers
echo "Removing stopped containers..."
docker container prune -f

# Remove unused images
echo "Removing unused images..."
docker image prune -f

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove build cache
echo "Removing build cache..."
docker builder prune -f

# Show space reclaimed
echo ""
echo "📊 Space after cleanup:"
docker system df

echo ""
echo "✅ Docker cleanup complete!"
echo "💡 You can now run: ./scripts/test-with-act.sh" 