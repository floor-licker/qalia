#!/bin/bash
set -e

echo "🚀 Starting Qalia UI server setup..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
apt install -y curl wget git unzip nginx certbot python3-certbot-nginx software-properties-common

# Install Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    rm get-docker.sh
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Create application directory if it doesn't exist
if [ ! -d "/opt/qalia" ]; then
    echo "📁 Creating application directory..."
    mkdir -p /opt/qalia
fi

# Remove old Python-based systemd service if it exists
echo "🗑️  Removing old qalia service if it exists..."
systemctl stop qalia || true
systemctl disable qalia || true
rm -f /etc/systemd/system/qalia.service

# Set up systemd service for UI Docker container
echo "🔧 Setting up Qalia UI systemd service..."
cat > /etc/systemd/system/qalia-ui.service << 'EOF'
[Unit]
Description=Qalia UI Docker Container
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/qalia/ui
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
Restart=no

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx for UI application
echo "🌐 Configuring Nginx for Qalia UI..."
cat > /etc/nginx/sites-available/qalia << 'EOF'
server {
    listen 80;
    server_name _;  # Accept any domain for now
    
    # Increase client max body size for file uploads
    client_max_body_size 50M;
    
    # Static files from React build
    location /assets/ {
        proxy_pass http://localhost:8000/assets/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cache static assets
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API routes
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Long timeouts for OAuth and API calls
        proxy_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
        proxy_connect_timeout 10s;
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Favicon
    location /vite.svg {
        proxy_pass http://localhost:8000/vite.svg;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # All other routes serve the React SPA
    location / {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Standard timeouts for UI
        proxy_timeout 30s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
        proxy_connect_timeout 5s;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/qalia /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

# Enable systemd service
systemctl daemon-reload
systemctl enable qalia-ui

echo "✅ Qalia UI server setup completed!"
echo "📝 Next steps:"
echo "  1. Clone your repository to /opt/qalia"
echo "  2. Navigate to /opt/qalia/ui directory"
echo "  3. Run 'docker-compose up --build -d'"
echo "  4. Start the qalia-ui service with 'systemctl start qalia-ui'"
echo "  5. Your Qalia UI will be available at http://your-server-ip/"
echo ""
echo "🔧 Useful commands:"
echo "  - Check service: systemctl status qalia-ui"
echo "  - View logs: docker-compose -f /opt/qalia/ui/docker-compose.yml logs"
echo "  - Restart: systemctl restart qalia-ui" 