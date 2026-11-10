# B站热门视频 TOP 100 前端

Vue 3、TypeScript、Pinia、Naive UI 和 ECharts 6 实现的响应式热榜界面。

## 环境

- Node.js 22.12+
- 后端服务：http://127.0.0.1:8000

建议从项目根目录运行 `start-all.bat` 或 `start-all.sh`。单独开发前端时：

```bash
npm ci
npm run dev
```

前端地址为 http://127.0.0.1:3000（`strictPort`，端口被占用会直接报错而不是悄悄换端口），`/api` 与 WebSocket 由 Vite 代理到后端。

## 检查命令

```bash
npm run typecheck
npm run test:unit   # vitest：工具函数 + Pinia store
npm run build
npm run test:e2e    # Playwright，需要前后端已启动
npm audit
```

E2E 需要前后端服务已经启动；首次运行前执行 `npx playwright install chromium`。

离线跑 E2E（不访问 B 站，CI 采用这条路径）：

```bash
cd ../bilibili-hot100-backend
python tests/make_fixture.py ../data/snapshot.json   # 生成 100 条假数据快照
BILIBILI_PRELOAD=0 python -m uvicorn main:app --port 8000
```

## 结构

```text
src/
├── api/          # 后端 API 封装
├── components/   # 页面组件
├── stores/       # Pinia 状态与统计
├── types/        # TypeScript 数据契约
└── utils/        # 格式化工具与图片兜底常量
tests/            # Playwright E2E
```
