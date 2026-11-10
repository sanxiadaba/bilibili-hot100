# Installation Guide

## For Claude (Anthropic)

### Method 1: Project Knowledge

1. Open Claude Desktop
2. Go to Settings → Project Knowledge
3. Click "Add Content"
4. Paste the content from `AI_INSTRUCTIONS.md`
5. Save

### Method 2: System Prompt

Add to your system prompt:

```
You have access to the bilibili-hot100-launcher skill.
When user wants to start the project, run:
- Windows: .\start-all.bat
- macOS/Linux: ./start-all.sh

Services:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
```

## For OpenClaw

Add to `skills.yaml`:

```yaml
skills:
  - name: bilibili-hot100-launcher
    trigger: 
      - "启动项目"
      - "run bilibili"
      - "start project"
    action:
      windows: ".\\start-all.bat"
      macos: "./start-all.sh"
      linux: "./start-all.sh"
```

## For Custom AI Assistants

### Step 1: Copy Files

Copy these files to your project:
```
z_bilibili/
├── skill.json              # Skill definition
├── AI_INSTRUCTIONS.md      # AI behavior instructions
└── scripts/
    ├── start-all.bat       # Windows launcher
    └── start-all.sh        # macOS/Linux launcher
```

### Step 2: Parse skill.json

Your AI should read `skill.json` and extract:
- `triggers.keywords` - When to activate
- `actions` - What command to run per OS
- `services` - URLs to display

### Step 3: Implement Handler

```python
def handle_bilibili_launcher(user_input, os_type):
    # Check if input matches triggers
    if matches_trigger(user_input, skill["triggers"]):
        # Get command for OS
        command = skill["actions"][os_type]["command"]
        # Execute
        run_command(command)
        # Return service URLs
        return skill["services"]
```

## For Trae / other IDE skill loaders

This repository ships the skill definition itself; nothing is pre-installed outside it.
Point your skill loader at `skill.json` and `AI_INSTRUCTIONS.md` in the repository root, and
let `actions.<os>.command` invoke the wrapper scripts.

## Verification

Test the installation:

1. Say: "启动bilibili项目"
2. AI should run `start-all.bat --detached --json` (or the `.sh` equivalent)
3. The command prints one JSON line with `"ok": true` and both service URLs
4. Open http://127.0.0.1:3000

## Troubleshooting

**Script not found:**
- The wrappers live in the repository root (`start-all.*`, `stop-all.*`); `scripts/` only mirrors them
- Check file permissions (chmod +x on Unix)

**Python not found:**
- The wrappers need a `python`/`python3` (3.11+) on PATH; the backend venv is created by `launcher.py`

**Ports blocked:**
- Run `python launcher.py --status` to see what the launcher thinks is running, or
  `Get-NetTCPConnection -State Listen -LocalPort 3000,8000` to find the owner
- Stop the conflicting application; the launcher intentionally does not kill unrelated processes

**Dependencies missing:**
- Install Python 3.11+ and Node.js 22.12+
