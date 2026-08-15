# RAG 知识库前端 (Web UI)

基于 Vue 3 + Element Plus 的前端界面，提供本地文档智能问答与辅助创作功能。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Element Plus** - 基于 Vue 3 的组件库
- **Pinia** - Vue 3 状态管理
- **Vue Router** - 路由管理
- **Axios** - HTTP 客户端
- **Vite** - 构建工具

## 功能模块

### 1. 首页 (`/`)
- 系统概览和统计信息
- 快捷操作入口
- 核心功能介绍

### 2. 知识库管理 (`/knowledge`)
- 文档目录同步
- 知识库统计信息
- 文件列表管理
- 清空/删除操作

### 3. 智能问答 (`/qa`)
- 对话式问答界面
- 支持多轮对话
- 显示参考来源
- 展示检索片段

### 4. 文档创作 (`/creation`)
- 10 种创作类型（报告/总结/方案/笔记/摘要/扩写/缩写/改写/结构化/自定义）
- 实时创作结果预览
- 支持复制和导出
- 显示参考文档

### 5. 系统设置 (`/settings`)
- API 服务配置
- 数据库配置
- 模型选择
- 系统信息

## 快速开始

### 安装依赖

```bash
cd webui
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 生产构建

```bash
npm run build
```

构建输出到 `dist/` 目录

## 目录结构

```
webui/
├── src/
│   ├── api/              # API 接口
│   │   └── index.js
│   ├── components/       # 公共组件
│   ├── router/           # 路由配置
│   │   └── index.js
│   ├── stores/           # Pinia 状态管理
│   │   └── app.js
│   ├── views/            # 页面组件
│   │   ├── Home.vue      # 首页
│   │   ├── Knowledge.vue # 知识库管理
│   │   ├── QA.vue        # 智能问答
│   │   ├── Creation.vue  # 文档创作
│   │   └── Settings.vue  # 系统设置
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── index.html
├── package.json
└── vite.config.js
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取系统状态 |
| `/api/sync` | POST | 同步文档 |
| `/api/ask` | POST | 智能问答 |
| `/api/create` | POST | 文档创作 |
| `/api/clear` | POST | 清空知识库 |
| `/api/remove` | POST | 删除文件 |

## 环境变量

前端通过 Vite 代理连接后端，无需额外配置。

如需修改后端地址，编辑 `vite.config.js`：

```js
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // 修改此处
      changeOrigin: true
    }
  }
}
```

## 界面预览

### 首页
- 系统统计卡片
- 快捷操作按钮
- 功能说明

### 知识库管理
- 文档同步表单
- 同步结果展示
- 文件列表表格

### 智能问答
- 对话历史区域
- 问题输入框
- 检索片段展示
- 参考来源标签

### 文档创作
- 创作类型选择
- 需求输入
- 结果预览
- 复制/导出功能

## 开发规范

### 组件命名
- 页面组件：大驼峰（Home.vue, QA.vue）
- 公共组件：大驼峰带前缀（ElButton, ElCard）

### 代码风格
- 使用 Composition API (`<script setup>`)
- 使用 Pinia 进行状态管理
- 使用 Vue Router 进行路由管理
- API 调用统一封装在 `src/api/` 目录

### 样式规范
- 使用 Scoped CSS
- 遵循 Element Plus 设计规范
- 响应式布局使用 Element Plus Grid 系统

## 浏览器支持

- Chrome >= 90
- Firefox >= 90
- Safari >= 14
- Edge >= 90

## License

MIT
