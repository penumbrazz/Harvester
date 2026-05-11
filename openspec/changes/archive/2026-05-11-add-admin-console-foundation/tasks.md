## 1. Frontend Tooling

- [x] 1.1 创建 `frontend/` Vite + React + TypeScript 工程结构和基础脚本
- [x] 1.2 配置 ESLint、Prettier、TypeScript strict mode 和无分号/单引号格式规则
- [x] 1.3 配置前端测试工具和 E2E 测试入口，确保后续测试可访问真实 API

## 2. Tests First

- [x] 2.1 编写应用壳渲染测试，覆盖默认概览页、导航和空页面状态
- [x] 2.2 编写 API 连接状态测试，覆盖 `/health` 成功和失败状态
- [x] 2.3 编写 E2E 测试，覆盖打开控制台、配置 API 地址/token、导航页面和检查 `data-testid`

## 3. Implementation

- [x] 3.1 实现 `DESIGN.md` 对应的 CSS variables、基础排版、按钮、输入框、卡片和状态 pill 样式
- [x] 3.2 实现应用布局、左侧导航、页面路由和业务页面占位
- [x] 3.3 实现 API client、base URL/token 配置、Authorization header 注入和错误归一化
- [x] 3.4 实现 `/health` 连接检查、加载状态、错误状态和重试入口

## 4. Verification

- [x] 4.1 运行前端格式化、lint、类型检查和单元/组件测试
- [x] 4.2 启动真实 Harvester API 和前端 dev server，运行 E2E 测试
- [x] 4.3 更新 README 或开发文档，说明前端启动、API 配置和测试命令
