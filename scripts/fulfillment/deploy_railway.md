# Deploy to Railway in 3 Minutes

Railway is the simplest way to deploy. No server management needed!

## Steps:

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Login**:
   ```bash
   railway login
   ```

3. **Deploy**:
   ```bash
   # From project root
   railway up
   ```

4. **Set Environment Variables**:
   ```bash
   railway variables set ENVIRONMENT=production
   railway variables set SHOPIFY_SHOP_DOMAIN=gracefulbydesign.myshopify.com
   # ... etc for each variable in .env
   ```

5. **Get Your URL**:
   ```bash
   railway domain
   ```

That's literally it! Railway handles:
- ✅ SSL certificates automatically
- ✅ Always running
- ✅ Auto-restarts if crashes
- ✅ Easy logs: `railway logs`

Cost: ~$5/month for this app

Your webhook URL will be something like:
`https://your-app.up.railway.app/webhooks/shopify/order-create`