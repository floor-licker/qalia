#!/bin/bash

# Qalia UI Launcher Script
# This script builds and launches the containerized Qalia UI demo

set -e

echo "🚀 Qalia UI Launcher"
echo "===================="
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it and try again."
    echo "   You can also use 'docker compose' (without hyphen) if you have Docker Compose V2"
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Build and start the services
echo "🔨 Building and starting Qalia UI..."
echo "   This may take a few minutes on first run..."
echo ""

docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for the service to be healthy
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo ""
        echo "✅ Qalia UI is ready!"
        echo ""
        echo "🌐 Open your browser and visit:"
        echo "   👉 http://localhost:8000"
        echo ""
        echo "💡 Features available:"
        echo "   • GitHub OAuth demo (simulated)"
        echo "   • Modern React UI with Mantine components"
        echo "   • Repository management interface"
        echo "   • Test recording session placeholders"
        echo ""
        echo "📋 Management commands:"
        echo "   • View logs:    docker-compose logs -f"
        echo "   • Stop:         docker-compose down"
        echo "   • Restart:      docker-compose restart"
        echo "   • Health check: curl http://localhost:8000/health"
        echo ""
        break
    fi
    
    sleep 5
    elapsed=$((elapsed + 5))
    echo -n "."
done

if [ $elapsed -ge $timeout ]; then
    echo ""
    echo "⚠️  Service seems to be taking longer than expected to start."
    echo "   Check the logs with: docker-compose logs"
    echo "   You can still try accessing: http://localhost:8000"
fi

echo ""
echo "🎯 To stop the UI later, run: docker-compose down" 