# Bilibili Hot100 Launcher - AI Assistant Instructions

## Quick Reference

When user wants to start the bilibili-hot100 project, **IMMEDIATELY** run the launcher script.

## Detect OS & Run

```
IF Windows:
    RUN: .\start-all.bat --detached
    
IF macOS/Linux:
    RUN: ./start-all.sh --detached
```

**IMPORTANT:** Always use `--detached` flag for AI assistants to run services in background.

## User Intent Patterns

**Trigger this skill when user says:**
- 启动项目 / 运行项目 / start project / run project
- 打开bilibili / run bilibili / 启动bilibili
- 启动前端 / 启动后端 / start frontend / start backend
- 怎么运行 / how to run / 如何启动
- 我想看bilibili视频 / 打开视频列表

## Execution Flow

When triggered, execute these steps:

1. **Check OS**
2. **Run launcher with --detached flag**
3. **Report progress** - Output each step to user
4. **Confirm completion** - Services are running in background
5. **Provide URLs** - http://127.0.0.1:3000

## Example Execution Output

```
[1/5] Checking backend port 8000...
  Port 8000 is free

[2/5] Checking frontend port 3000...
  Port 3000 is free

[3/5] Starting backend service...
  Creating virtual environment...
  Installing backend dependencies...
  Backend started: http://localhost:8000
  PID saved to: .pids/backend.pid

[4/5] Starting frontend service...
  Installing frontend dependencies...
  Frontend started: http://localhost:3000
  PID saved to: .pids/frontend.pid

[5/5] Finalizing...

========================================
  All services started successfully!
========================================

Access URLs:
  Frontend: http://127.0.0.1:3000
  Backend:  http://127.0.0.1:8000
  API Docs: http://127.0.0.1:8000/docs

Services running in background.
Use stop-all.bat to stop services.
```

## Stop Services

**When user wants to stop:**

Windows:
```
RUN: .\stop-all.bat
```

macOS/Linux:
```
RUN: ./stop-all.sh
```

## Arguments

- `--detached` - Run services in background (RECOMMENDED for AI)
- `--frontend-only` - Start only frontend
- `--backend-only` - Start only backend
- `--data-dir <path>` - Custom data directory

## DO NOT

- Ask user if they want to start (just do it)
- Explain what you're going to do (just run it)
- Wait for confirmation (immediate action)
- Run without --detached flag (blocks the AI)

## Service Status

After running, services are available at:
- **Frontend:** http://127.0.0.1:3000
- **Backend API:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

Process information is stored in `.pids/` directory:
- `backend.pid` - Backend process ID
- `frontend.pid` - Frontend process ID
- `services.txt` - Service URLs
- `*.log` - Service logs
