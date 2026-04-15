#!/bin/bash

# Bilibili Hot100 Stopper
# Stop all running services

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Bilibili Hot100 Stopper${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"

# Check if PID files exist
if [ ! -d "$PID_DIR" ]; then
    echo -e "${YELLOW}No PID directory found. Services may not be running.${NC}"
    echo ""
    echo "Attempting to force kill by port..."
    FORCE_KILL=true
else
    FORCE_KILL=false
fi

# Stop backend
echo -e "${YELLOW}[1/2] Stopping backend service...${NC}"
if [ -f "$PID_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$PID_DIR/backend.pid")
    echo -e "  Found backend PID: $BACKEND_PID"
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill -9 $BACKEND_PID 2>/dev/null || true
        echo -e "  ${GREEN}Backend stopped successfully${NC}"
    else
        echo -e "  Backend process not found (already stopped?)"
    fi
    rm -f "$PID_DIR/backend.pid"
else
    echo -e "  Backend PID file not found"
fi
echo ""

# Stop frontend
echo -e "${YELLOW}[2/2] Stopping frontend service...${NC}"
if [ -f "$PID_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
    echo -e "  Found frontend PID: $FRONTEND_PID"
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill -9 $FRONTEND_PID 2>/dev/null || true
        echo -e "  ${GREEN}Frontend stopped successfully${NC}"
    else
        echo -e "  Frontend process not found (already stopped?)"
    fi
    rm -f "$PID_DIR/frontend.pid"
else
    echo -e "  Frontend PID file not found"
fi
echo ""

# Force kill by port if needed
if [ "$FORCE_KILL" = true ]; then
    echo -e "Force killing processes on ports 3000 and 8000..."
    for port in 3000 8000; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            pid=$(lsof -Pi :$port -sTCP:LISTEN -t)
            echo -e "  Killing process on port $port (PID: $pid)"
            kill -9 $pid 2>/dev/null || true
        fi
    done
    echo ""
fi

# Clean up PID directory
if [ -d "$PID_DIR" ]; then
    rm -rf "$PID_DIR"
    echo -e "${GREEN}Cleaned up PID files${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  All services stopped${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
