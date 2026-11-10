# Usage Examples

## Example 1: Chinese User

**User:** 我想启动bilibili项目

**AI runs:** `.\start-all.bat --detached --json`

**AI Response:**
```
正在为您启动 Bilibili Hot100 项目...

Starting backend (FastAPI on :8000)...
  Backend is ready: http://127.0.0.1:8000
Starting frontend (Vite on :3000)...
  Frontend is ready: http://127.0.0.1:3000

访问地址:
  前端: http://127.0.0.1:3000
  后端: http://127.0.0.1:8000
  API文档: http://127.0.0.1:8000/docs
```

## Example 2: English User

**User:** How do I run the bilibili project?

**AI runs:** `.\start-all.bat --detached --json`

**AI Response:**
```
Starting Bilibili Hot100 project for you...

  Backend is ready: http://127.0.0.1:8000
  Frontend is ready: http://127.0.0.1:3000

Access URLs:
  Frontend: http://127.0.0.1:3000
  Backend:  http://127.0.0.1:8000
  API Docs: http://127.0.0.1:8000/docs

Services are running in the background.
```

## Example 3: Frontend Only

**User:** 只启动前端

**AI Action:**
```bash
.\start-all.bat --frontend-only
```

## Example 4: Backend Only

**User:** Start only the backend

**AI Action:**
```bash
.\start-all.bat --backend-only
```

## Example 5: Port Conflict Resolution

**User:** 端口被占用了怎么办？

**AI Response:**
```
启动器会拒绝终止不属于本项目的进程。先确认端口占用者：

Windows:
Get-NetTCPConnection -State Listen -LocalPort 3000,8000 | Select-Object LocalPort, OwningProcess

macOS/Linux:
lsof -nP -iTCP:3000 -iTCP:8000 -sTCP:LISTEN

确认进程身份后关闭对应应用，再重新运行启动脚本。
```

## Example 6: First Time Setup

**User:** 第一次运行需要做什么？

**AI Response:**
```
首次运行会自动完成以下步骤：

1. 创建 Python 虚拟环境 (.venv)
2. 安装后端依赖 (pip install)
3. 安装前端依赖 (npm ci)
4. 启动服务并打开浏览器

您只需要运行：
.\start-all.bat

然后等待几分钟让依赖安装完成即可。
```

## Example 7: Stop Services

**User:** 怎么停止服务？

**AI Response:**
```
停止服务的方法：

方法1: 在终端窗口按 Ctrl+C
方法2: 关闭终端窗口
后台模式请运行项目停止脚本：

Windows:
.\stop-all.bat

macOS/Linux:
./stop-all.sh
```
