# Usage Examples

## Example 1: Chinese User

**User:** 我想启动bilibili项目

**AI Response:**
```
正在为您启动 Bilibili Hot100 项目...

[1/4] 检查后端口 8000...
  端口 8000 可用

[2/4] 检查前端端口 3000...
  端口 3000 可用

[3/4] 启动后端服务...
  后端启动中: http://localhost:8000
  等待后端就绪...
  后端已就绪!

[4/4] 启动前端服务...
  正在打开浏览器...

========================================
  所有服务启动成功!
========================================

访问地址:
  前端: http://localhost:3000
  后端: http://localhost:8000
  API文档: http://localhost:8000/docs

按 Ctrl+C 停止所有服务
```

## Example 2: English User

**User:** How do I run the bilibili project?

**AI Response:**
```
Starting Bilibili Hot100 project for you...

[1/4] Checking backend port 8000...
  Port 8000 is free

[2/4] Checking frontend port 3000...
  Port 3000 is free

[3/4] Starting backend service...
  Backend starting: http://localhost:8000
  Waiting for backend to be ready...
  Backend is ready!

[4/4] Starting frontend service...
  Opening browser...

========================================
  All services started successfully!
========================================

Access URLs:
  Frontend: http://localhost:3000
  Backend:  http://localhost:8000
  API Docs: http://localhost:8000/docs

Press Ctrl+C to stop all services
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
