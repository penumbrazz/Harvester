## Why

Harvester 的核心价值在于把 raw evidence 抽取成可搜索的 `content_item / item_version / chunk`，但当前只能通过 search API/CLI 查询。需要一个内容库界面，让用户浏览、搜索并追溯已采集内容，同时保持 raw/content 分层边界。

## What Changes

- 新增 content item 列表 API，返回 item ID、类型、source、topic、标题、canonical URL、状态、最新版本时间和必要摘要。
- 复用并扩展现有 `GET /items/search` 前端交互，支持关键词/向量搜索模式、分页、source/topic 过滤和结果状态展示。
- 新增内容库页面，支持 grid/list 切换、搜索、过滤、结果空状态和错误反馈。
- 搜索结果只展示 content item / version / chunk 级可追溯字段，不暴露 raw HTML/API payload。
- E2E 必须通过真实 API 写入 fixture 或测试数据后验证前端可搜索、可切换视图。

## Capabilities

### New Capabilities

- `admin-content-library`: 管理控制台的内容库浏览、搜索、过滤和结果溯源能力。

### Modified Capabilities

- 无。

## Impact

- 后端新增 content item list read API；现有 `search-api-cli` 行为不破坏。
- 前端新增 content library 页面、搜索组件、结果卡片/表格和 API 类型。
- 测试新增 API 列表测试、搜索集成测试和前端真实 HTTP E2E。
- 依赖 `add-admin-console-foundation`；可在 search API 已稳定后独立实现。
