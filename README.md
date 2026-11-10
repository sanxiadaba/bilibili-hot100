# B站热门视频 TOP 100

![](docs/screenshot-home.png)

> B站热门视频排行榜，支持实时爬取、数据可视化、热榜分析

## ✨ 功能特点

- 📊 **热榜爬取** — 并发抓取 B站热门视频 TOP 100，实时更新
- 🖼️ **本地缓存** — 视频封面 / UP主头像按 URL hash 去重，避免重复下载
- 📈 **数据分析** — 播放量、点赞、投币、收藏、弹幕多维统计，ECharts 图表展示
- 🌙 **深色模式** — 支持明暗主题切换
- 📜 **实时日志** — WebSocket 推送爬取过程日志
- 📦 **一键启动** — Windows / macOS / Linux 全平台脚本，零配置运行

## 🖥️ 界面预览

### 视频列表页

![视频列表页](docs/screenshot-home.png)

### 数据分析页

![数据分析页](docs/screenshot-stats.png)

## 🚀 快速开始

### 环境要求

| 环境 | 版本要求 |
|------|---------|
| Python | 3.11+ |
| Node.js | 22.12+ |
| 操作系统 | Windows 10+ / macOS 10.15+ / Ubuntu 18.04+ |

> Python 版本下限由依赖决定（`starlette 1.10` 要求 ≥3.11），低于此版本会在 `pip install` 阶段失败。

### 启动方式

**Windows:**
```bash
.\start-all.bat
```

**macOS / Linux:**
```bash
chmod +x start-all.sh
./start-all.sh
```

所有平台逻辑都在 `launcher.py` 里，`start-all.*` / `stop-all.*` 只是转发器。脚本会自动：
1. 检测端口和已登记的服务进程，端口冲突时安全退出
2. 创建 Python 虚拟环境，安装后端依赖
3. 安装前端 npm 包
4. 启动后端服务（FastAPI on :8000）和前端（Vite on :3000）
5. 前台模式自动打开浏览器；`--detached` 模式启动后立即返回，服务在后台独立运行

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://127.0.0.1:3000 |
| 后端 API | http://127.0.0.1:8000 |
| API 文档 | http://127.0.0.1:8000/docs |

### 启动参数

```bash
# 仅启动前端
.\start-all.bat --frontend-only

# 仅启动后端
.\start-all.bat --backend-only

# 自定义数据目录（Windows）
.\start-all.bat --data-dir D:\bilibili-data

# 自定义数据目录（macOS / Linux）
./start-all.sh --data-dir /custom/path

# 后台运行（AI 助手使用），返回结构化结果
.\start-all.bat --detached --json

# 查看服务状态（不启动任何东西）
python launcher.py --status
```

`--json` 输出示例：

```json
{"ok": true, "mode": "all", "detached": true,
 "backend": {"pid": 19208, "url": "http://127.0.0.1:8000", "ready": true},
 "frontend": {"pid": 11476, "url": "http://127.0.0.1:3000", "ready": true}}
```

失败时输出 `{"ok": false, "error": "..."}` 并以非零码退出。

### 停止服务

```bash
# Windows
.\stop-all.bat

# macOS / Linux
./stop-all.sh
```

## 🛠️ 技术栈

### 后端

- **框架**: Python 3.11+ / FastAPI
- **爬虫**: aiohttp（异步并发，失败退避重试）
- **图片缓存**: 按日期分目录存储，URL hash 去重
- **持久化**: 原子 JSON 快照 `snapshot.json`（重启先加载，再后台刷新）+ 按次导出

### 前端

- **框架**: Vue 3 + TypeScript
- **构建**: Vite 8
- **UI 库**: Naive UI
- **图表**: ECharts 6（按需加载）
- **状态管理**: Pinia

## 📁 项目结构

```
bilibili-hot100/
├── bilibili-hot100-backend/       # Python FastAPI 后端
│   ├── main.py                   # ASGI 入口（uvicorn main:app）
│   ├── hot100/                   # 后端实现
│   │   ├── config.py             # 环境变量与常量
│   │   ├── models.py             # 对外数据契约
│   │   ├── logs.py               # 日志环形缓冲 + WebSocket 广播
│   │   ├── images.py             # 图片缓存（内容寻址 + 清理）
│   │   ├── storage.py            # 快照 / 导出 / 保留策略
│   │   ├── crawler.py            # 抓取、重试、校验
│   │   ├── state.py              # 缓存与刷新编排
│   │   └── api.py                # 路由与 CORS
│   ├── requirements.txt          # 运行依赖
│   ├── requirements-dev.txt      # 测试依赖（httpx2 / ruff）
│   ├── pyproject.toml            # （仓库根）ruff 配置
│   └── tests/                    # 单元 + API 测试、离线夹具
│
├── bilibili-hot100-vue3-ts/       # Vue3 前端
│   ├── src/
│   │   ├── api/                  # 后端 API 调用
│   │   ├── components/           # Vue 组件
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── types/                # TypeScript 类型定义
│   │   └── utils/                # 工具函数（含 img 兜底常量）
│   ├── package.json
│   └── vite.config.ts
│
├── launcher.py                    # 跨平台启动器（唯一的启动/停止实现）
├── start-all.bat / start-all.sh   # 转发到 launcher.py
├── stop-all.bat / stop-all.sh     # 转发到 launcher.py --stop
├── pyproject.toml                 # ruff 配置（Python 侧唯一配置源）
├── scripts/                       # 兼容旧路径的同名转发脚本
├── data/                          # 运行数据（不纳入 Git）
│   ├── snapshot.json              # 最后一次成功抓取（启动时优先加载）
│   ├── cache/images/              # 封面 / 头像缓存
│   └── data_exports/              # 每次刷新的 JSON 导出（默认保留 14 天）
└── docs/                         # 截图
```

## 🔧 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/hot100` | GET | 获取热榜数据（只读缓存；`?force_refresh=true` 返回 400）|
| `/api/refresh` | POST | 触发后台数据刷新（校验 Origin）|
| `/api/status` | GET | 服务状态（含 `is_partial` / `source` / `snapshot_time` / `cache_ttl_seconds`）|
| `/api/images/{date}/{file}` | GET | 获取缓存图片（`immutable` 强缓存）|
| `/api/exports` | GET | 导出列表，`?limit=` 限制返回的日期目录数 |
| `/api/exports/latest` | GET | 最新一次导出的完整内容 |
| `/api/logs` | GET | 历史日志 |
| `/api/logs/ws` | WebSocket | 实时日志流 |

`/api/hot100` 在数据不完整时返回 `is_partial: true`（前端会显示"数据不完整"标签），`source` 为 `live`（本次抓取）或 `snapshot`（启动时从快照恢复）。

> 刷新只走 `POST /api/refresh`：以前 `GET /api/hot100?force_refresh=true` 会直接触发抓取，任意网页用一个 `<img>` 就能让爬虫持续工作，现已改为返回 400。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BILIBILI_DATA_DIR` | `data/` | 快照、图片缓存、导出的根目录 |
| `BILIBILI_HOST` / `BILIBILI_PORT` | `127.0.0.1` / `8000` | 后端监听地址（`python main.py` 时生效）|
| `BILIBILI_PRELOAD` | `1` | 启动时是否立即后台抓取；`0` 表示只用快照 |
| `BILIBILI_CACHE_TTL` | `300` | `/api/hot100` 视为"新鲜"的秒数 |
| `BILIBILI_MIN_VIDEOS` | `90` | 少于该条数则判定抓取失败 |
| `BILIBILI_ALLOWED_ORIGINS` | `127.0.0.1:3000`、`localhost:3000`、`4173` | CORS / 刷新 / WS 允许的来源（逗号分隔）|
| `BILIBILI_EXPORT_RETENTION_DAYS` | `14` | 导出目录保留天数 |
| `BILIBILI_IMAGE_ORPHAN_DAYS` | `30` | 索引外图片的清理宽限期 |
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Vite 代理目标 |
| `VITE_WS_URL` | 同源 `/api/logs/ws` | 覆盖日志 WebSocket 地址 |

## 🐛 常见问题

**端口被占用？**
```powershell
Get-NetTCPConnection -State Listen -LocalPort 3000,8000 |
    Select-Object LocalPort, OwningProcess
```
启动器不会终止不属于本项目的进程。请确认占用者后自行关闭，或先运行 `stop-all` 停止已登记的项目服务。

**Python / Node 缺失？**
- Python: https://python.org （需要 3.11+）
- Node.js: https://nodejs.org （需要 22.12+）

**页面显示"数据不完整"？**
本次只抓到 90–99 条（B 站分页偶发缺页或个别视频字段异常）。数据仍然可用，下一次刷新会自动恢复；连续出现请查看 `/api/logs`。

**图片缓存失效？**
项目会自动维护 URL 到实际文件的 `downloaded_urls.json` 索引；索引失效时会验证并自动修复。启动时还会加载 `data/snapshot.json`，即使 B 站暂时不可用也能显示上一次的数据。

**`--detached` 之后怎么确认状态？**
```bash
python launcher.py --status
```
输出 JSON，包含每个服务的 `pid` / `port_in_use` / `ready` / `owned`。

## ✅ 提交前检查

```bash
# 后端（在仓库根目录跑 lint，配置见 pyproject.toml）
ruff check .
ruff format --check .

# 后端单元 + 接口测试
cd bilibili-hot100-backend
python -m unittest discover -s tests -v

# 前端类型、单测、构建和 E2E
cd ../bilibili-hot100-vue3-ts
npm run typecheck
npm run test:unit
npm run build
npm run test:e2e
npm audit
```

E2E 需要前后端已启动。想离线跑（CI 就是这么做的）：先 `python tests/make_fixture.py ../data/snapshot.json`，再以 `BILIBILI_PRELOAD=0` 启动后端。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

[Apache License 2.0](LICENSE)
