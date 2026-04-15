# B站热门视频 TOP 100 - TypeScript 前端

使用 Vue 3 + TypeScript + Pinia + Naive UI + ECharts 重构的前端项目。

## 特性

- **TypeScript 全类型支持** - 完整的类型定义和类型安全
- **4列视频网格布局** - 充分利用桌面端屏幕空间
- **白天/黑夜主题切换** - 支持自动保存主题偏好
- **实时日志查看器** - WebSocket 连接查看后端日志
- **数据分析图表** - ECharts 可视化展示数据统计
- **分类筛选和排序** - 多维度视频筛选和排序

## 项目结构

```
src/
├── api/
│   └── backend.ts      # API 请求封装
├── components/
│   ├── AppHeader.vue   # 顶部导航栏
│   ├── CategoryFilter.vue  # 分类筛选
│   ├── LogViewer.vue   # 日志查看器
│   ├── StatsCharts.vue # 统计图表
│   ├── StatsView.vue   # 数据分析页面
│   ├── ThemeToggle.vue # 主题切换按钮
│   ├── VideoCard.vue   # 视频卡片组件
│   └── VideoList.vue   # 视频列表 (4列布局)
├── stores/
│   ├── theme.ts        # 主题状态管理
│   └── videos.ts       # 视频数据状态管理
├── types/
│   └── index.ts        # TypeScript 类型定义
├── utils/
│   └── format.ts       # 格式化工具函数
├── App.vue
└── main.ts
```

## 启动步骤

### 1. 安装依赖

```bash
cd C:\qoder_work\bilibili-hot100-vue3-ts
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

前端服务将在 http://localhost:3003 启动

### 3. 确保后端服务已启动

后端服务需要在 http://localhost:8000 运行。

```bash
cd C:\qoder_work\bilibili-hot100-backend
# 确保已安装依赖
pip install -r requirements.txt
# 启动后端
python main.py
```

## 技术栈

- Vue 3.4 + Composition API
- TypeScript 5.3
- Pinia 状态管理
- Naive UI 组件库
- ECharts 图表库
- Vite 构建工具

## 布局说明

视频网格采用响应式4列布局：
- 大屏幕 (1600px+): 4列
- 中等屏幕 (1200px): 3列
- 小屏幕 (900px): 2列
- 移动端 (600px): 1列
