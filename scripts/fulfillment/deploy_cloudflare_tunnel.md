# Deploy with Cloudflare Tunnel (Best Option!)

Cloudflare Tunnel creates a secure connection from your computer (or any server) to Cloudflare's network. 

**Cost: FREE** (yes, completely free!)

## Why This Is Perfect:

- ✅ **FREE** - No hosting costs
- ✅ Automatic SSL certificate
- ✅ Works from your computer OR DigitalOcean
- ✅ More reliable than ngrok
- ✅ Permanent URL (doesn't change)
- ✅ Built-in DDoS protection

## Setup (10 minutes):

### 1. Install Cloudflare Tunnel:

**Mac:**
```bash
brew install cloudflare/cloudflare/cloudflared
```

**Linux/DigitalOcean:**
```bash
# Add cloudflare gpg key
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

# Add repo
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared focal main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

# Install
sudo apt-get update && sudo apt-get install cloudflared
```

### 2. Login to Cloudflare:
```bash
cloudflared tunnel login
```
(Opens browser, select your domain)

### 3. Create Tunnel:
```bash
cloudflared tunnel create grooved-fulfillment
```

### 4. Create Config File:

Create `~/.cloudflared/config.yml`:
```yaml
url: http://localhost:8750
tunnel: <YOUR-TUNNEL-ID>
credentials-file: /home/YOUR-USER/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: fulfillment.your-domain.com
    service: http://localhost:8750
  - service: http_status:404
```

### 5. Add DNS Record:

```bash
cloudflared tunnel route dns grooved-fulfillment fulfillment.your-domain.com
```

### 6. Run It:

**Quick Test:**
```bash
# Terminal 1: Start your app
uv run fulfillment/main.py

# Terminal 2: Start tunnel
cloudflared tunnel run grooved-fulfillment
```

**Production (as a service):**
```bash
sudo cloudflared service install
sudo systemctl start cloudflared
```

## Your Webhook URL:
`https://fulfillment.your-domain.com/webhooks/shopify/order-create`

## That's It!

No servers to manage, completely free, enterprise-grade infrastructure!

## Comparison:

| Option | Cost | Setup Time | Reliability |
|--------|------|------------|-------------|
| Cloudflare Tunnel | FREE | 10 min | Excellent |
| ngrok | Free/Paid | 2 min | Good |
| Railway | $5/mo | 5 min | Good |
| DigitalOcean | $0* | 30 min | Good |

*Using your existing droplet

## Quick Start Commands:

```bash
# 1. Start your fulfillment server
uv run fulfillment/main.py

# 2. In another terminal, start tunnel
cloudflared tunnel run grooved-fulfillment

# 3. Your app is now live at https://fulfillment.your-domain.com!
```