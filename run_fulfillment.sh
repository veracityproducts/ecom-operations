#!/bin/bash
# Start the fulfillment API server

echo "🚀 Starting Grooved Learning Fulfillment API..."
echo "   URL: http://localhost:8750"
echo "   Docs: http://localhost:8750/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd fulfillment && uv run uvicorn main:app --reload --port 8750