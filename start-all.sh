#!/bin/bash

# Bilibili Hot100 Launcher
# One-click launcher for bilibili-hot100 project

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Bilibili Hot100 Launcher${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Configuration
FRONTEND_PORT=3000
BACKEND_PORT=8000
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default data directory (can be customized via environment variable or argument)
DATA_DIR="${DATA_DIR:-$SCRIPT_DIR/data}"

# Parse arguments
MODE="all"
DETACHED=false
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
        --detached)
            DETACHED=true
            shift
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo -e "[Mode] $MODE"
echo -e "[Detached] $DETACHED"
echo -e "[Data Dir] $DATA_DIR"
echo ""

# =============================================
# Discover Python executable
# =============================================
echo -e "${YELLOW}[0/5] Discovering Python...${NC}"
PYTHON_BIN=""
PYTHON_VER=""

# Try python3 first
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    PYTHON_VER=$(python3 --version 2>&1)
fi

# Try python as fallback
if [ -z "$PYTHON_BIN" ] && command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
    PYTHON_VER=$(python --version 2>&1)
fi

if [ -z "$PYTHON_BIN" ]; then
    echo -e "  ${RED}ERROR: Python not found. Please install Python 3.8+${NC}"
    echo "  Download: https://python.org"
    exit 1
fi

echo -e "  Found: $PYTHON_VER ($PYTHON_BIN)"
echo ""

# Create PID directory
PID_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PID_DIR"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    if check_port $port; then
        local pid=$(lsof -Pi :$port -sTCP:LISTEN -t)
        echo -e "  Found process PID: $pid, terminating..."
        kill -9 $pid 2>/dev/null || true
        echo -e "  ${GREEN}Process terminated${NC}"
    fi
}

# Clear backend port
echo -e "${YELLOW}[1/5] Checking backend port $BACKEND_PORT...${NC}"
kill_port $BACKEND_PORT
echo -e "  ${GREEN}Port $BACKEND_PORT is free${NC}"
echo ""

# Clear frontend port
echo -e "${YELLOW}[2/5] Checking frontend port $FRONTEND_PORT...${NC}"
kill_port $FRONTEND_PORT
echo -e "  ${GREEN}Port $FRONTEND_PORT is free${NC}"
echo ""

# Start backend if needed
if [ "$MODE" != "frontend" ]; then
    echo -e "${YELLOW}[3/5] Starting backend service...${NC}"
    cd "$SCRIPT_DIR/bilibili-hot100-backend"

    # Create data directory if not exists
    if [ ! -d "$DATA_DIR" ]; then
        echo -e "  Creating data directory: $DATA_DIR"
        mkdir -p "$DATA_DIR"
    fi

    # Check if venv exists and is working (fastapi installed)
    if [ -d ".venv" ] && .venv/bin/pip show fastapi >/dev/null 2>&1; then
        echo -e "  Virtual environment already exists and fastapi is installed, skipping venv creation."
        # But still upgrade pip and deps in case requirements changed
        .venv/bin/pip install --upgrade pip >/dev/null 2>&1
        .venv/bin/pip install -r requirements.txt >/dev/null 2>&1
    else
        if [ -d ".venv" ]; then
            echo -e "  Removing stale virtual environment..."
            rm -rf .venv
        fi
        echo -e "  Creating virtual environment..."
        $PYTHON_BIN -m venv .venv
        echo -e "  Installing backend dependencies..."
        .venv/bin/pip install --upgrade pip >/dev/null 2>&1
        .venv/bin/pip install -r requirements.txt >/dev/null 2>&1
        echo -e "  ${GREEN}Dependencies installed${NC}"
    fi
    echo ""

    # Start backend in background
    echo -e "  Starting backend process..."
    export DATA_DIR="$DATA_DIR"
    nohup .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > "$PID_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$PID_DIR/backend.pid"

    echo -e "  ${GREEN}Backend started: http://localhost:$BACKEND_PORT${NC}"
    echo -e "  PID saved to: $PID_DIR/backend.pid"
    echo ""

    # Wait for backend to be ready
    echo -e "  Waiting for backend to be ready..."
    sleep 3
    echo -e "  ${GREEN}Backend is ready${NC}"
    echo ""
fi

# Start frontend if needed
if [ "$MODE" != "backend" ]; then
    echo -e "${YELLOW}[4/5] Starting frontend service...${NC}"
    cd "$SCRIPT_DIR/bilibili-hot100-vue3-ts"

    # Check node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "  Installing frontend dependencies..."
        npm install >/dev/null 2>&1
        echo -e "  ${GREEN}Dependencies installed${NC}"
    fi

    # In detached mode: build for production, then serve dist
    # In foreground mode: run dev server directly (no nohup needed, script keeps running)
    if [ "$DETACHED" = true ]; then
        echo -e "  Building frontend for production..."
        npm run build >/dev/null 2>&1
        echo -e "  ${GREEN}Build completed${NC}"

        echo -e "  Starting frontend server..."
        nohup npx serve -s dist -l $FRONTEND_PORT > "$PID_DIR/frontend.log" 2>&1 &
        FRONTEND_PID=$!
    else
        echo -e "  Starting frontend dev server..."
        npm run dev -- --port $FRONTEND_PORT > "$PID_DIR/frontend.log" 2>&1 &
        FRONTEND_PID=$!
    fi

    echo $FRONTEND_PID > "$PID_DIR/frontend.pid"
    echo -e "  ${GREEN}Frontend started: http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  PID saved to: $PID_DIR/frontend.pid"
    echo ""
fi

echo -e "${YELLOW}[5/5] Finalizing...${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  All services started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Access URLs:"
echo -e "  Frontend: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  Backend:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
echo -e "  API Docs: ${BLUE}http://localhost:$BACKEND_PORT/docs${NC}"
echo -e "  Python:   ${BLUE}$PYTHON_VER${NC}"
echo -e "  Data Dir: ${BLUE}$DATA_DIR${NC}"
echo ""
echo -e "Process files:"
echo -e "  Backend PID: $PID_DIR/backend.pid"
echo -e "  Frontend PID: $PID_DIR/frontend.pid"
echo ""

# Save service info
echo "Frontend: http://localhost:$FRONTEND_PORT" > "$PID_DIR/services.txt"
echo "Backend: http://localhost:$BACKEND_PORT" >> "$PID_DIR/services.txt"
echo "API Docs: http://localhost:$BACKEND_PORT/docs" >> "$PID_DIR/services.txt"

# Open browser
echo -e "Opening browser..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:$FRONTEND_PORT" &
elif command -v open >/dev/null 2>&1; then
    open "http://localhost:$FRONTEND_PORT" &
fi

if [ "$DETACHED" = true ]; then
    echo ""
    echo -e "${GREEN}Services running in background.${NC}"
    echo -e "Use ${YELLOW}./stop-all.sh${NC} to stop services."
    echo ""
    exit 0
fi

echo ""
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo ""

# Keep script running to maintain foreground process
trap 'echo ""; echo -e "${RED}Stopping services...${NC}"; bash "$SCRIPT_DIR/stop-all.sh"; exit 0' INT
while true; do
    sleep 5
done
