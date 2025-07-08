# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/ui

# Copy package files
COPY ui/package*.json ./

# Install dependencies
RUN npm install

# Copy source code (exclude node_modules and other build artifacts)
COPY ui/src ./src
COPY ui/public ./public
COPY ui/index.html ./
COPY ui/vite.config.ts ./
COPY ui/tsconfig.json ./
COPY ui/tsconfig.node.json ./
COPY ui/postcss.config.js ./
COPY ui/tailwind.config.js ./

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
RUN pip install --no-cache-dir -r requirements.txt

# Copy the demo server
COPY ui/ui_demo_server.py ./

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/ui/dist ./ui/dist

# No need for combined server - ui_demo_server.py already handles everything

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the demo server with GitHub OAuth
CMD ["python", "ui_demo_server.py"] 