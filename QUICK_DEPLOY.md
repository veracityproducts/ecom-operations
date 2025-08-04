# Quick Deploy to DigitalOcean + Cloudflare (15 minutes)

This is the simplest way to deploy your fulfillment system using your existing DigitalOcean droplet and FREE Cloudflare Tunnel.

## What You'll Get
- ✅ Professional URL: `https://fulfillment.your-domain.com`
- ✅ Automatic SSL certificate
- ✅ 24/7 uptime (runs on your droplet)
- ✅ Your computer can be OFF
- ✅ Total cost: $0 extra

## Step 1: Upload Files to Droplet (5 minutes)

### Option A: Using SCP (Recommended)
```bash
# From your local project directory
scp -r fulfillment/ root@YOUR_DROPLET_IP:/opt/
scp pyproject.toml uv.lock .env root@YOUR_DROPLET_IP:/opt/fulfillment/
```

### Option B: Using Git
```bash
# On your droplet
cd /opt
git clone YOUR_REPO_URL fulfillment
```

## Step 2: SSH into Your Droplet
```bash
ssh root@YOUR_DROPLET_IP
cd /opt/fulfillment
```

## Step 3: Install Dependencies (3 minutes)
```bash
# Install UV (Python package manager)
curl -LsSf https://astral-sh.github.io/uv/install.sh | sh
source ~/.bashrc

# Install Python dependencies
uv sync

# Test that it works
uv run fulfillment/main.py
# Press Ctrl+C after you see "Uvicorn running"
```

## Step 4: Install Cloudflare Tunnel (2 minutes)
```bash
# Add Cloudflare repository
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared focal main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

# Install
sudo apt-get update && sudo apt-get install cloudflared -y
```

## Step 5: Set Up Tunnel (5 minutes)
```bash
# Login (opens browser)
cloudflared tunnel login
# Select your domain when prompted

# Create tunnel
cloudflared tunnel create fulfillment

# Create config file
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Paste this config (replace YOUR-DOMAIN.com):
```yaml
url: http://localhost:8750
tunnel: fulfillment
credentials-file: /root/.cloudflared/fulfillment.json

ingress:
  - hostname: fulfillment.YOUR-DOMAIN.com
    service: http://localhost:8750
  - service: http_status:404
```

```bash
# Add DNS record
cloudflared tunnel route dns fulfillment fulfillment.YOUR-DOMAIN.com
```

## Step 6: Run Everything (2 minutes)

### Quick Test First:
```bash
# Terminal 1 (or use screen)
uv run fulfillment/main.py

# Terminal 2 (or new screen)
cloudflared tunnel run fulfillment

# Test it works
curl https://fulfillment.YOUR-DOMAIN.com/health
```

### Production Setup with Screen:
```bash
# Install screen if needed
apt-get install screen -y

# Start fulfillment app
screen -S fulfillment -dm bash -c 'cd /opt/fulfillment && uv run fulfillment/main.py'

# Start Cloudflare tunnel
screen -S tunnel -dm cloudflared tunnel run fulfillment

# Check they're running
screen -ls
```

## Step 7: Update Shopify Webhook

1. Go to Shopify Admin → Settings → Notifications → Webhooks
2. Create new webhook for "Order creation"
3. URL: `https://fulfillment.YOUR-DOMAIN.com/webhooks/shopify/order-create`
4. Format: JSON
5. API version: 2024-10

## Done! 🎉

Your fulfillment system is now running 24/7 on your droplet with a professional HTTPS URL.

## Useful Commands

```bash
# View logs
screen -r fulfillment  # (Ctrl+A, D to detach)
screen -r tunnel

# Restart services
screen -X -S fulfillment quit
screen -X -S tunnel quit
# Then run the screen commands again

# Check if services are running
curl https://fulfillment.YOUR-DOMAIN.com/health

# View all screens
screen -ls
```

## Troubleshooting

If webhook signature fails:
- Make sure SHOPIFY_WEBHOOK_SECRET in .env matches Shopify

If Cloudflare tunnel won't start:
- Check the tunnel name matches in config.yml
- Run `cloudflared tunnel list` to see your tunnels

## Next Steps

1. Test with a single order first!
2. Monitor logs for any errors
3. Switch to ENVIRONMENT=production when ready
4. Consider setting up systemd services for auto-restart