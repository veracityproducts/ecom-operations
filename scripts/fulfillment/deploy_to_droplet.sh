#!/bin/bash
# Deployment script for existing DigitalOcean droplet

echo "🚀 Deploying Fulfillment System to DigitalOcean Droplet"
echo "======================================================"

# Configuration
DROPLET_IP="YOUR_DROPLET_IP"
DROPLET_USER="root"  # or your user
APP_DIR="/opt/fulfillment"
SERVICE_NAME="fulfillment"

# Check if IP is set
if [ "$DROPLET_IP" = "YOUR_DROPLET_IP" ]; then
    echo "❌ Please update DROPLET_IP in this script with your droplet's IP address"
    exit 1
fi

echo "📦 Step 1: Preparing deployment package..."
# Create deployment directory
mkdir -p deployment_temp
cp -r fulfillment deployment_temp/
cp pyproject.toml deployment_temp/
cp uv.lock deployment_temp/
cp .env deployment_temp/

# Create systemd service file
cat > deployment_temp/fulfillment.service << 'EOF'
[Unit]
Description=Grooved Learning Fulfillment Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/fulfillment
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/uv run python fulfillment/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📤 Step 2: Uploading files to droplet..."
# Copy files to droplet
scp -r deployment_temp/* $DROPLET_USER@$DROPLET_IP:$APP_DIR/

echo "🔧 Step 3: Setting up on droplet..."
# SSH commands to set up the service
ssh $DROPLET_USER@$DROPLET_IP << 'ENDSSH'
# Install UV if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral-sh.github.io/uv/install.sh | sh
    export PATH="/root/.cargo/bin:$PATH"
fi

# Install Python if needed
uv python install 3.12

# Go to app directory
cd /opt/fulfillment

# Create virtual environment and install dependencies
uv sync

# Set up systemd service
cp fulfillment.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable fulfillment
systemctl restart fulfillment

# Check status
systemctl status fulfillment
ENDSSH

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update nginx configuration for SSL/proxy"
echo "2. Set webhook URL in Shopify to: https://your-domain.com/webhooks/shopify/order-create"
echo "3. Monitor logs: ssh $DROPLET_USER@$DROPLET_IP 'journalctl -u fulfillment -f'"

# Cleanup
rm -rf deployment_temp