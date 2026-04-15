# Bilibili Hot100 Launcher Skill

A complete, self-contained skill package for AI assistants to launch the bilibili-hot100 project with one click.

## 📦 What's Included

This package contains **everything needed** to run the project:

```
z_bilibili/
├── skill.json                      # Machine-readable skill definition
├── AI_INSTRUCTIONS.md              # AI behavior instructions
├── INSTALL.md                      # Installation guide
├── README.md                       # This file
├── start-all.bat                   # Windows launcher (root level)
├── start-all.sh                    # macOS/Linux launcher (root level)
├── bilibili-hot100-backend/        # ✅ Python FastAPI backend (FULL CODE)
│   ├── main.py
│   ├── requirements.txt
│   ├── crawler/
│   ├── database/
│   └── ...
├── bilibili-hot100-vue3-ts/        # ✅ Vue3 frontend (FULL CODE)
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
├── scripts/                        # Launcher scripts backup
│   ├── start-all.bat
│   └── start-all.sh
├── docs/                           # Documentation
└── examples/                       # Usage examples
```

## 🚀 Quick Start

### For Users

1. **Extract** the `z_bilibili` folder
2. **Double-click** `start-all.bat` (Windows) or run `./start-all.sh` (macOS/Linux)
3. **Browser opens automatically** at http://localhost:3000

That's it! No additional setup needed.

### For AI Assistants

**When user says:**
- "启动项目" / "运行项目" / "start project"
- "打开bilibili" / "run bilibili"
- "启动前端" / "启动后端"
- "怎么运行" / "how to run"

**Action:**
```bash
# Windows
.\start-all.bat

# macOS/Linux
./start-all.sh
```

## ✨ Features

- ✅ **Complete Project** - Includes ALL source code
- ✅ **Zero Configuration** - Works out of the box
- ✅ **Auto Dependencies** - Installs Python/Node packages automatically
- ✅ **Auto Port Management** - Clears ports 3000 & 8000
- ✅ **Auto Browser** - Opens http://localhost:3000
- ✅ **Cross-Platform** - Windows, macOS, Linux

## 🌐 Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Vue3 + TypeScript + Vite UI |
| Backend API | http://localhost:8000 | Python FastAPI |
| API Docs | http://localhost:8000/docs | Swagger Documentation |

## 📋 System Requirements

- **OS**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.8+ (with pip)
- **Node.js**: 16+ (with npm)

## 🔧 What the Scripts Do

1. **Check Ports** - Kill any processes using ports 3000/8000
2. **Setup Backend**:
   - Create Python virtual environment (`.venv`)
   - Install requirements: `pip install -r requirements.txt`
   - Start FastAPI server on port 8000
3. **Setup Frontend**:
   - Install npm packages: `npm install`
   - Start Vite dev server on port 3000
4. **Open Browser** - Launch default browser at http://localhost:3000

## 📁 Project Structure

### Backend (`bilibili-hot100-backend/`)
- **Framework**: Python + FastAPI
- **Database**: SQLite
- **Crawler**: Async Bilibili API crawler
- **Features**: Hot100 videos, data analysis, WebSocket logs

### Frontend (`bilibili-hot100-vue3-ts/`)
- **Framework**: Vue 3 + TypeScript
- **Build Tool**: Vite
- **UI Library**: Naive UI
- **Charts**: ECharts
- **Features**: Video list, data visualization, dark mode

## 🛠️ Installation for AI Platforms

### Claude (Anthropic)

1. Copy `z_bilibili` folder to project
2. Add `AI_INSTRUCTIONS.md` to Project Knowledge
3. Done! Claude can now start the project

### OpenClaw

Add to skills config:
```yaml
skills:
  bilibili-launcher:
    path: "z_bilibili"
    triggers: ["启动项目", "start project"]
    action: "start-all.bat|start-all.sh"
```

### Custom AI Assistants

Parse `skill.json`:
```python
import json

with open('z_bilibili/skill.json') as f:
    skill = json.load(f)

# Extract triggers
triggers = skill['triggers']['keywords']

# Extract commands
windows_cmd = skill['actions']['windows']['command']
macos_cmd = skill['actions']['macos']['command']
```

## 📝 Arguments

- `--frontend-only` - Start only frontend
- `--backend-only` - Start only backend

Examples:
```bash
# Frontend only
.\start-all.bat --frontend-only

# Backend only
./start-all.sh --backend-only
```

## 🛑 Stop Services

- **Method 1**: Press `Ctrl+C` in terminal
- **Method 2**: Close terminal window
- **Method 3**: Run kill command

## 🐛 Troubleshooting

### Port Already in Use

**Windows:**
```powershell
Get-NetTCPConnection -LocalPort 3000,8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**macOS/Linux:**
```bash
lsof -ti:3000,8000 | xargs kill -9
```

### Missing Python/Node

Install from:
- Python: https://python.org
- Node.js: https://nodejs.org

## 📄 License

MIT License - Free to use and distribute

## 🙋 Support

See [INSTALL.md](INSTALL.md) for detailed instructions.

---

**Complete project included - Ready to run!** 🚀
