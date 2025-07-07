# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/ui

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Python backend with built frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir fastapi uvicorn

# Copy the demo server
COPY ui_demo_server.py ./

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/ui/dist ./ui/dist

# Create a combined server that serves both frontend and API
COPY <<EOF ./combined_server.py
#!/usr/bin/env python3
"""
Combined server that serves both the React app and the API
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import our demo server
from ui_demo_server import app as demo_app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mount the built React app
ui_dist_path = Path("/app/ui/dist")
if ui_dist_path.exists():
    demo_app.mount("/static", StaticFiles(directory=str(ui_dist_path)), name="static")
    
    @demo_app.get("/", include_in_schema=False)
    @demo_app.get("/auth", include_in_schema=False)
    @demo_app.get("/record/{path:path}", include_in_schema=False)
    @demo_app.get("/tests/{path:path}", include_in_schema=False)
    async def serve_spa():
        """Serve the React SPA for all non-API routes"""
        return FileResponse(str(ui_dist_path / "index.html"))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Qalia UI (Containerized)")
    print("📍 Application: http://localhost:8000")
    print("📍 API Health: http://localhost:8000/health")
    print("")
    print("💡 The UI is now fully self-contained!")
    print("   • Frontend and backend are served from the same port")
    print("   • Demo OAuth flow is included")
    print("   • No external dependencies required")
    print("")
    
    uvicorn.run(demo_app, host="0.0.0.0", port=8000, log_level="info")
EOF

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the combined server
CMD ["python", "combined_server.py"] 