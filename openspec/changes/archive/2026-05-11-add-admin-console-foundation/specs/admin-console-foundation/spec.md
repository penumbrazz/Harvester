## ADDED Requirements

### Requirement: Admin console frontend shell
系统 SHALL 提供一个基于 React、TypeScript 和 Vite 的管理控制台前端应用壳。

#### Scenario: Open admin console shell
- **WHEN** 用户打开前端开发服务器或构建后的管理控制台入口
- **THEN** 系统 MUST 显示 Harvester 管理控制台布局、导航和默认概览页面

#### Scenario: Navigate placeholder pages
- **WHEN** 用户点击信息源、Recipes、Schedules、爬取任务、作业队列、内容库或审计日志导航项
- **THEN** 系统 MUST 切换到对应页面占位状态且不刷新整个浏览器页面

### Requirement: Design system tokens follow DESIGN.md
系统 SHALL 将根目录 `DESIGN.md` 中的视觉规则落地为可复用前端 design tokens 和基础样式。

#### Scenario: Render Notion-inspired visual language
- **WHEN** 管理控制台渲染按钮、输入框、卡片、状态 pill 和导航
- **THEN** UI MUST 使用温暖中性色、`#0075de` 主交互色、1px whisper border、克制阴影和指定圆角体系

### Requirement: API connection configuration
系统 SHALL 允许用户配置 Harvester API base URL 和 API token，并通过真实 HTTP API 检查连接状态。

#### Scenario: Healthy API connection
- **WHEN** 用户配置有效 API base URL 且后端 `/health` 返回成功
- **THEN** 前端 MUST 显示已连接状态

#### Scenario: Missing or unreachable API
- **WHEN** API base URL 不可访问或 `/health` 返回错误
- **THEN** 前端 MUST 显示连接失败状态和可操作的配置入口

### Requirement: Frontend test foundation
系统 SHALL 提供前端单元/组件测试和 E2E 测试基础，并保留交互元素的 `data-testid`。

#### Scenario: Run frontend verification
- **WHEN** 开发者执行前端 lint、类型检查、测试和 E2E 命令
- **THEN** 命令 MUST 能验证应用壳、导航、连接状态和关键交互元素
