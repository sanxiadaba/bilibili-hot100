#!/bin/bash

# Bilibili Hot100 Launcher
# One-click startup script for macOS/Linux

set -e

FRONTEND_PORT=3000
BACKEND_PORT=8000
MODE="all"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --frontend-only)
            MODE="frontend"
            shift
            ;;
        --backend-only)
            MODE="backend"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Bilibili Hot100 Launcher${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "[Mode] ${MODE}"
echo ""

# Function to kill process on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Checking port $port...${NC}"
    
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "  Found process on port $port"
        kill -9 $(lsof -ti:$port) 2>/dev/null || true
        echo "  Process terminated"
    else
        echo -e "${GREEN}  Port $port is free${NC}"
    fi
}

# Clear backend port
if [ "$MODE" != "frontend" ]; then
    kill_port $BACKEND_PORT
    echo ""
fi

# Clear frontend port
if [ "$MODE" != "backend" ]; then
    kill_port $FRONTEND_PORT
    echo ""
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start backend
if [ "$MODE" != "frontend" ]; then
    echo -e "${CYAN}[3/4] Starting backend service...${NC}"
    cd "$SCRIPT_DIR/bilibili-hot100-backend"
    
    # Check virtual environment
    if [ ! -d ".venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv .venv
    fi
    
    # Install requirements if needed
    if [ ! -f ".venv/lib/python3.*/site-packages/fastapi" ] && [ ! -d ".venv/lib/python3.*/site-packages/fastapi" ]; then
        echo "  Installing backend dependencies..."
        source .venv/bin/activate
        pip install -r requirements.txt
    else
        source .venv/bin/activate
    fi
    
    # Start backend in background
    python -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
    BACKEND_PID=$!
    echo -e "${GREEN}  Backend starting: http://localhost:$BACKEND_PORT (PID: $BACKEND_PID)${NC}"
    echo ""
    
    # Wait for backend
    echo "  Waiting for backend to be ready..."
    sleep 3
    echo -e "${GREEN}  Backend should be ready now${NC}"
    echo ""
fi

# Start frontend
if [ "$MODE" != "backend" ]; then
    echo -e "${CYAN}[4/4] Starting frontend service...${NC}"
    cd "$SCRIPT_DIR/bilibili-hot100-vue3-ts"
    
    # Check node_modules
    if [ ! -d "node_modules" ]; then
        echo "  Installing frontend dependencies..."
        npm install
    fi
    
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${GREEN}  All services started successfully!${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo "Access URLs:"
    echo -e "  Frontend: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  Backend:  ${GREEN}http://localhost:$BACKEND_PORT${NC}"
    echo -e "  API Docs: ${GREEN}http://localhost:$BACKEND_PORT/docs${NC}"
    echo ""
    echo "Press Ctrl+C to stop all services"
    echo ""
    
    # Open browser
    echo "Opening browser..."
    if command -v open &> /dev/null; then
        open "http://localhost:$FRONTEND_PORT"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:$FRONTEND_PORT"
    fi
    
    # Start frontend (this will block)
    npm run dev -- --port $FRONTEND_PORT
fi

# If backend only mode
if [ "$MODE" == "backend" ]; then
    echo ""
    echo -e "${GREEN}Backend service is running on http://localhost:$BACKEND_PORT${NC}"
    echo "Press Ctrl+C to stop"
    echo ""
    wait $BACKEND_PID
fi

echo ""
echo "Services stopped."
