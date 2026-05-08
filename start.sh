#!/bin/bash
# Railway Startup Script
# Runs both Streamlit dashboard and background worker

set -e  # Exit on error

echo "============================================"
echo "🚀 JKT48 Monitor Startup Script"
echo "============================================"
echo "📍 Current directory: $(pwd)"
echo "📁 Files in directory:"
ls -la
echo "============================================"

# Install missing dependencies (backup)
echo "📦 Checking dependencies..."
pip install pytz 2>&1 | grep -i "already\|successfully" || echo "✅ pytz installed"

# Create output directory if not exists
echo "📂 Creating output directory..."
mkdir -p /mnt/user-data/outputs
echo "✅ Output directory ready"

# Check if background_monitor.py exists
if [ ! -f "background_monitor.py" ]; then
    echo "❌ ERROR: background_monitor.py not found!"
    exit 1
fi

# Start background worker in background
echo "============================================"
echo "📊 Starting background worker..."
python background_monitor.py &
WORKER_PID=$!
echo "✅ Worker started with PID: $WORKER_PID"

# Wait a moment for worker to initialize
echo "⏳ Waiting 2 seconds for worker to initialize..."
sleep 2

# Check if worker is still running
if ps -p $WORKER_PID > /dev/null; then
    echo "✅ Background worker is running!"
else
    echo "❌ ERROR: Background worker failed to start!"
    exit 1
fi

# Start Streamlit (foreground process)
echo "============================================"
echo "🌐 Starting Streamlit dashboard..."
streamlit run jkt48_stock_monitor.py --server.port=$PORT --server.address=0.0.0.0
