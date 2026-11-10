# Bilibili Hot100 Launcher - AI Assistant Instructions

## Quick Reference

When user wants to start the bilibili-hot100 project, **IMMEDIATELY** run the launcher script.

## Detect OS & Run

```
IF Windows:
    RUN: .\start-all.bat --detached --json
    
IF macOS/Linux:
    RUN: ./start-all.sh --detached --json
```

**IMPORTANT:** Always use `--detached` so the command returns instead of blocking.

The command returns a single JSON line; parse it instead of scraping text:

```json
{"ok": true, "backend": {"pid": 19208, "ready": true, "url": "..."},
 "frontend": {"pid": 11476, "ready": true, "url": "..."}}
```

Failure returns `{"ok": false, "error": "..."}` with a non-zero exit code.

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
2. **Run launcher with `--detached --json`**
3. **Read the JSON result** instead of parsing the human-readable text
4. **Confirm completion** - `"ok": true` means both services are ready
5. **Provide URLs** - http://127.0.0.1:3000

## Example Execution Output

```
Starting backend (FastAPI on :8000)...
  Backend is ready: http://127.0.0.1:8000
Starting frontend (Vite on :3000)...
  Frontend is ready: http://127.0.0.1:3000
Bilibili Hot100 services started successfully.
{"backend": {"pid": 19208, "ready": true, "url": "http://127.0.0.1:8000"},
 "data_dir": "...\\data", "detached": true,
 "frontend": {"pid": 11476, "ready": true, "url": "http://127.0.0.1:3000"},
 "mode": "all", "ok": true}
```

The command returns as soon as the services are ready; it never blocks.
A failure exits non-zero and prints `{"ok": false, "error": "..."}`.

## Status / Troubleshooting

```
RUN: python launcher.py --status
RUN: python launcher.py --stop      # same as stop-all
```

`--status` reports `pid`, `alive`, `ready`, `owned`, `port_in_use` for each service.
Logs live in `.pids/backend.err.log` and `.pids/frontend.err.log`.

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
- `--json` - Print a machine-readable result (use together with `--detached`)
- `--status` - Report service state as JSON and exit
- `--frontend-only` - Start only frontend
- `--backend-only` - Start only backend
- `--data-dir <path>` - Custom data directory

## DO NOT

- Ask user if they want to start (just do it)
- Explain what you're going to do (just run it)
- Wait for confirmation (immediate action)
- Run without --detached flag (blocks the AI)

## Service Status

Check state without starting anything:

```
RUN: python launcher.py --status
```

`--status` always prints JSON, e.g. `{"ok": true, "backend": {"pid": 19208, "alive": true, "ready": true, "owned": true, ...}}`.

After running, services are available at:
- **Frontend:** http://127.0.0.1:3000
- **Backend API:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

Process information is stored in `.pids/` directory:
- `backend.pid` - Backend process ID
- `frontend.pid` - Frontend process ID
- `services.txt` - Service URLs
- `*.log` - Service logs
