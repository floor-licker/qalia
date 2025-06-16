#!/bin/bash
set -e

echo "🚀 Starting Qalia.ai server setup..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
apt install -y curl wget git unzip nginx certbot python3-certbot-nginx software-properties-common

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    rm get-docker.sh
fi

# Install Node.js 18
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt install -y nodejs
fi

# Install Python 3.11 and pip
echo "🐍 Installing Python 3.11..."
apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev

# Install system dependencies for Playwright
echo "🎭 Installing Playwright system dependencies..."
apt install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0

# Create application directory if it doesn't exist
if [ ! -d "/opt/qalia" ]; then
    echo "📁 Creating application directory..."
    mkdir -p /opt/qalia
fi

# Set up systemd service
echo "🔧 Setting up Qalia systemd service..."
cat > /etc/systemd/system/qalia.service << 'EOF'
[Unit]
Description=Qalia.ai GitHub App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qalia
Environment=PATH=/opt/qalia/venv/bin
ExecStart=/opt/qalia/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/qalia << 'EOF'
server {
    listen 80;
    server_name _;  # Accept any domain for now
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Long timeouts for analysis
        proxy_timeout 1800s;
        proxy_read_timeout 1800s;
        proxy_send_timeout 1800s;
        proxy_connect_timeout 60s;
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
systemctl enable qalia

echo "✅ Server setup completed!"
echo "📝 Next steps:"
echo "  1. Clone your repository to /opt/qalia"
echo "  2. Set up Python virtual environment"
echo "  3. Install dependencies"
echo "  4. Create .env file with your secrets"
echo "  5. Start the qalia service" 