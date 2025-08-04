#!/bin/bash
# Super simple deployment with ngrok for testing

echo "🚀 Quick Fulfillment System Setup with ngrok"
echo "==========================================="
echo ""
echo "This will get you running in 5 minutes!"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "📦 Installing ngrok..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install ngrok/ngrok/ngrok
    else
        echo "Please install ngrok from: https://ngrok.com/download"
        echo "Or run: curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo \"deb https://ngrok-agent.s3.amazonaws.com buster main\" | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install ngrok"
        exit 1
    fi
fi

echo "✅ Step 1: Start the fulfillment server"
echo "Run this in a new terminal:"
echo ""
echo "  uv run fulfillment/main.py"
echo ""
echo "Press Enter when the server is running..."
read

echo "✅ Step 2: Start ngrok tunnel"
echo "Run this in another terminal:"
echo ""
echo "  ngrok http 8750"
echo ""
echo "You'll see something like:"
echo "  Forwarding  https://abc123.ngrok.io -> http://localhost:8750"
echo ""
echo "That https URL is your webhook endpoint!"
echo ""
echo "✅ Step 3: Update Shopify webhook"
echo "1. Copy the ngrok HTTPS URL"
echo "2. Add /webhooks/shopify/order-create to it"
echo "3. Go to Shopify Admin → Settings → Notifications → Webhooks"
echo "4. Create webhook with your ngrok URL"
echo ""
echo "⚠️  IMPORTANT: ngrok URLs change each time you restart!"
echo "For permanent solution, we'll do the proper deployment later."
echo ""
echo "📋 Quick test commands:"
echo "  # Check if it's working:"
echo "  curl https://YOUR-NGROK-URL.ngrok.io/health"
echo ""
echo "That's it! You're ready to receive webhooks!"