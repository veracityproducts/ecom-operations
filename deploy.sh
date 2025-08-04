#!/bin/bash
# One-click deployment script for Grooved Learning Fulfillment

echo "🚀 Deploying to DigitalOcean Droplet"
echo "===================================="

# Configuration
DROPLET_IP="164.90.128.16"
DOMAIN="fulfillment.graceful-e.com"

# Create deployment package
echo "📦 Creating deployment package..."
tar -czf fulfillment-deploy.tar.gz fulfillment/ pyproject.toml uv.lock .env

# Upload to droplet
echo "📤 Uploading to droplet..."
scp fulfillment-deploy.tar.gz root@$DROPLET_IP:/tmp/

# Create setup script
cat > /tmp/setup-fulfillment.sh << 'EOF'
#!/bin/bash
set -e

echo "🔧 Setting up fulfillment system..."

# Extract files
cd /opt
rm -rf fulfillment
tar -xzf /tmp/fulfillment-deploy.tar.gz
cd fulfillment

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing UV..."
    curl -LsSf https://astral-sh.github.io/uv/install.sh | sh
    export PATH="/root/.cargo/bin:$PATH"
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
/root/.cargo/bin/uv sync

# Install Cloudflare Tunnel if not present
if ! command -v cloudflared &> /dev/null; then
    echo "🔐 Installing Cloudflare Tunnel..."
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
    echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared focal main' | tee /etc/apt/sources.list.d/cloudflared.list
    apt-get update && apt-get install cloudflared -y
fi

# Check if tunnel exists
if ! cloudflared tunnel list | grep -q "fulfillment"; then
    echo "🔐 Creating Cloudflare tunnel..."
    echo "⚠️  You'll need to run 'cloudflared tunnel login' manually first!"
    echo "Then re-run this script."
    exit 1
fi

# Create tunnel config
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << CONFIG
url: http://localhost:8750
tunnel: fulfillment
credentials-file: /root/.cloudflared/fulfillment.json

ingress:
  - hostname: DOMAIN_PLACEHOLDER
    service: http://localhost:8750
  - service: http_status:404
CONFIG

# Install screen if needed
apt-get install screen -y

# Stop existing screens if running
screen -X -S fulfillment quit 2>/dev/null || true
screen -X -S tunnel quit 2>/dev/null || true

# Start services
echo "🚀 Starting services..."
screen -S fulfillment -dm bash -c 'cd /opt/fulfillment && /root/.cargo/bin/uv run fulfillment/main.py'
screen -S tunnel -dm cloudflared tunnel run fulfillment

sleep 5

# Check if running
if screen -ls | grep -q fulfillment; then
    echo "✅ Fulfillment service started!"
else
    echo "❌ Failed to start fulfillment service"
fi

if screen -ls | grep -q tunnel; then
    echo "✅ Cloudflare tunnel started!"
else
    echo "❌ Failed to start tunnel"
fi

echo ""
echo "📋 Status:"
screen -ls

echo ""
echo "🎉 Deployment complete!"
echo "🔗 Your webhook URL: https://DOMAIN_PLACEHOLDER/webhooks/shopify/order-create"
echo ""
echo "📝 Useful commands:"
echo "  View app logs: screen -r fulfillment"
echo "  View tunnel logs: screen -r tunnel"
echo "  Detach from screen: Ctrl+A, then D"
EOF

# Replace domain in script
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /tmp/setup-fulfillment.sh

# Upload and run setup script
echo "🚀 Running setup on droplet..."
scp /tmp/setup-fulfillment.sh root@$DROPLET_IP:/tmp/
ssh root@$DROPLET_IP "chmod +x /tmp/setup-fulfillment.sh && /tmp/setup-fulfillment.sh"

# Cleanup
rm -f fulfillment-deploy.tar.gz
rm -f /tmp/setup-fulfillment.sh

echo ""
echo "✅ Deployment script complete!"
echo ""
echo "⚠️  IMPORTANT: If you see a message about Cloudflare login:"
echo "1. SSH into your droplet: ssh root@$DROPLET_IP"
echo "2. Run: cloudflared tunnel login"
echo "3. Select graceful-e.com in the browser"
echo "4. Run: /tmp/setup-fulfillment.sh"
echo ""
echo "Your webhook URL: https://$DOMAIN/webhooks/shopify/order-create"