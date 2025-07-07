#!/bin/bash

# Development script for Qalia UI
# Runs both FastAPI backend and Vite frontend

set -e

echo "🚀 Starting Qalia Development Environment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: Please run this script from the qalia root directory${NC}"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping development servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start FastAPI backend
echo -e "${BLUE}🐍 Starting FastAPI backend on port 8000...${NC}"
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD:$PYTHONPATH"
python src/web/app.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if ! curl -s http://localhost:8000/ui > /dev/null; then
    echo -e "${RED}❌ Backend failed to start${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✅ Backend started successfully${NC}"

# Start Vite frontend (if package.json exists)
if [ -f "ui/package.json" ]; then
    echo -e "${BLUE}⚡ Starting Vite frontend on port 3000...${NC}"
    cd ui
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
        npm install
    fi
    
    # Start development server
    npm run dev &
    FRONTEND_PID=$!
    
    echo -e "${GREEN}✅ Frontend development server started${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend not set up yet. Run 'npm install' in the ui/ directory first.${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Development environment ready!${NC}"
echo "=========================================="
echo -e "🌐 Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "🌐 Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "📡 API:      ${BLUE}http://localhost:8000/api${NC}"
echo -e "🔌 WebSocket: ${BLUE}ws://localhost:8000/ws${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"

# Wait for background processes
wait 