# Deployment Guide - DigitalOcean Droplet

This guide covers deploying the fulfillment system to your existing DigitalOcean droplet.

## Prerequisites

- Existing DigitalOcean droplet with Ubuntu
- Domain name pointing to your droplet (for SSL)
- Root or sudo access to the droplet

## Quick Deployment Steps

### 1. Prepare Your Droplet

SSH into your droplet and install required software:

```bash
# Connect to your droplet
ssh root@YOUR_DROPLET_IP

# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3 python3-pip nginx certbot python3-certbot-nginx

# Install UV package manager
curl -LsSf https://astral-sh.github.io/uv/install.sh | sh
source ~/.bashrc
```

### 2. Deploy the Application

On your local machine:

```bash
# Update the deployment script with your droplet IP
vi scripts/fulfillment/deploy_to_droplet.sh
# Change DROPLET_IP="YOUR_DROPLET_IP" to your actual IP

# Make it executable and run
chmod +x scripts/fulfillment/deploy_to_droplet.sh
./scripts/fulfillment/deploy_to_droplet.sh
```

### 3. Set Up Nginx with SSL

On your droplet:

```bash
# Copy nginx configuration
cp /opt/fulfillment/scripts/fulfillment/nginx_config_example.conf /etc/nginx/sites-available/fulfillment

# Edit the configuration
nano /etc/nginx/sites-available/fulfillment
# Replace 'your-domain.com' with your actual domain

# Enable the site
ln -s /etc/nginx/sites-available/fulfillment /etc/nginx/sites-enabled/
nginx -t  # Test configuration
systemctl reload nginx

# Get SSL certificate from Let's Encrypt
certbot --nginx -d your-domain.com
```

### 4. Configure Environment

On your droplet:

```bash
# Edit the production environment file
nano /opt/fulfillment/.env

# Set for production:
ENVIRONMENT=production
# Ensure all API tokens are correct
```

### 5. Start the Service

```bash
# Start and enable the service
systemctl start fulfillment
systemctl enable fulfillment

# Check status
systemctl status fulfillment

# View logs
journalctl -u fulfillment -f
```

## Manual Deployment (Alternative)

If you prefer manual deployment:

```bash
# 1. On your local machine, create a deployment package
tar -czf fulfillment.tar.gz fulfillment/ pyproject.toml uv.lock .env

# 2. Copy to droplet
scp fulfillment.tar.gz root@YOUR_DROPLET_IP:/opt/

# 3. On droplet, extract and set up
ssh root@YOUR_DROPLET_IP
cd /opt
tar -xzf fulfillment.tar.gz
cd fulfillment
uv sync

# 4. Run with PM2 (alternative to systemd)
npm install -g pm2
pm2 start "uv run python fulfillment/main.py" --name fulfillment
pm2 save
pm2 startup
```

## Verify Deployment

1. **Check API Health**:
   ```bash
   curl https://your-domain.com/health
   ```

2. **Check Nginx Logs**:
   ```bash
   tail -f /var/log/nginx/fulfillment_access.log
   ```

3. **Check Application Logs**:
   ```bash
   journalctl -u fulfillment -f
   ```

## Update Shopify Webhook

1. Go to Shopify Admin → Settings → Notifications → Webhooks
2. Update webhook URL to: `https://your-domain.com/webhooks/shopify/order-create`
3. Test with a single order first!

## Monitoring Commands

```bash
# Service status
systemctl status fulfillment

# Recent logs
journalctl -u fulfillment -n 100

# Follow logs
journalctl -u fulfillment -f

# Restart service
systemctl restart fulfillment

# Check port
netstat -tlnp | grep 8750
```

## Rollback

If something goes wrong:

```bash
# Stop the service
systemctl stop fulfillment

# Switch back to development mode
nano /opt/fulfillment/.env
# Set ENVIRONMENT=development

# Restart
systemctl start fulfillment
```

## Security Notes

- The `.env` file contains sensitive tokens - ensure proper permissions:
  ```bash
  chmod 600 /opt/fulfillment/.env
  chown www-data:www-data /opt/fulfillment/.env
  ```

- Consider using environment variables instead of `.env` file for production
- Set up firewall rules if not already done:
  ```bash
  ufw allow 22/tcp    # SSH
  ufw allow 80/tcp    # HTTP
  ufw allow 443/tcp   # HTTPS
  ufw enable
  ```

## Next Steps

1. Set up monitoring (UptimeRobot, DataDog, etc.)
2. Configure log rotation
3. Set up automated backups
4. Plan for database migration from JSON to PostgreSQL/Airtable

Remember to test with a single order before processing bulk orders!