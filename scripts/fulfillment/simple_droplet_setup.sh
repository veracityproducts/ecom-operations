#!/bin/bash
# Super Simple Setup for DigitalOcean + Cloudflare Tunnel

echo "🚀 Simple Fulfillment Setup on Your Droplet"
echo "=========================================="
echo ""
echo "Run these commands on your DigitalOcean droplet:"
echo ""

cat << 'EOF'
# 1. Install UV (Python package manager)
curl -LsSf https://astral-sh.github.io/uv/install.sh | sh
source ~/.bashrc

# 2. Clone or copy your project
cd /opt
# Option A: Clone from git
git clone YOUR_REPO fulfillment

# Option B: Or upload files
# (Use FileZilla or scp to upload your fulfillment folder)

# 3. Install dependencies
cd /opt/fulfillment
uv sync

# 4. Install Cloudflare Tunnel
# For Ubuntu:
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared focal main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install cloudflared

# 5. Login to Cloudflare (opens browser)
cloudflared tunnel login

# 6. Create tunnel
cloudflared tunnel create grooved-fulfillment

# 7. Create simple startup script
cat > /opt/fulfillment/start.sh << 'SCRIPT'
#!/bin/bash
cd /opt/fulfillment
uv run fulfillment/main.py
SCRIPT

chmod +x /opt/fulfillment/start.sh

# 8. Run both services with screen
screen -S fulfillment -dm /opt/fulfillment/start.sh
screen -S tunnel -dm cloudflared tunnel run grooved-fulfillment

echo "✅ Done! Your fulfillment system is running!"
echo "Check status: screen -ls"
echo "View logs: screen -r fulfillment"
EOF

echo ""
echo "📋 Quick Reference:"
echo "- Start app: screen -S fulfillment -dm /opt/fulfillment/start.sh"
echo "- Start tunnel: screen -S tunnel -dm cloudflared tunnel run grooved-fulfillment"
echo "- Check what's running: screen -ls"
echo "- View app logs: screen -r fulfillment"
echo "- View tunnel logs: screen -r tunnel"
echo "- Detach from screen: Ctrl+A, then D"