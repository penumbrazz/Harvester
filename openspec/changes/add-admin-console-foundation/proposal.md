## Why

Harvester 已经具备 API、CLI、调度、抓取、队列、搜索和审计基座，但日常 home lab 运维仍主要依赖命令行和零散 API。需要先建立一个真实连接后端的前端控制台基础层，为后续信息源、任务、内容、审计等页面提供一致的工程结构和视觉约束。

## What Changes

- 新增前端工程基础：React + TypeScript + Vite 单页应用、路由壳、全局布局、API client、错误处理和加载状态。
- 按根目录 `DESIGN.md` 建立 Notion 风格设计 token：温暖中性色、whisper border、低饱和状态 pill、Notion Blue 主交互色、4px/12px 圆角体系。
- 建立管理控制台信息架构导航，但只实现 foundation 所需的健康状态、连接状态和空页面占位。
- 支持配置 Harvester API base URL 和 API token，所有后续前端页面通过真实 HTTP API 访问后端。
- 为后续 E2E 测试建立 Playwright 或等价测试入口，并在交互元素上保留/新增 `data-testid`。
- 不在本 change 中实现信息源、任务、内容、审计或 recipe/schedule 的业务页面。

## Capabilities

### New Capabilities

- `admin-console-foundation`: 管理控制台前端基础能力，包括工程结构、视觉 token、应用壳、导航、API client、认证 token 配置、健康检查和前端测试基座。

### Modified Capabilities

- 无。

## Impact

- 新增前端目录、Node 工具链配置、格式化/lint/test 脚本。
- 可能更新 Docker Compose 或 README，说明如何本地启动 API 与前端。
- 后端仅需确认 `/health` 可被前端读取；不新增业务 API。
- 后续 change 建议顺序执行：`add-admin-source-management`、`add-admin-recipes-schedules`、`add-admin-operations-observability`、`add-admin-content-library`、`add-admin-audit-log`。
