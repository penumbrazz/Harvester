## Why

多个前端页面（Sources、Recipes、Schedules、Crawls、Jobs）当前一次性加载全部数据，没有分页控件。随着数据量增长，这些页面将面临性能问题和糟糕的用户体验。部分后端 API 已支持 limit/offset 参数但前端未使用；部分后端 API 还返回扁平数组，需要改造为分页响应格式。

## What Changes

- 为以下页面添加统一的前端分页组件和逻辑：Sources、Recipes、Schedules、Crawls、Jobs
- 改造 Sources、Recipes、Schedules 三个后端 API，从返回扁平数组改为返回 `{ items, total, limit, offset }` 分页响应格式
- 前端 Crawls 和 Jobs 页面接入已有的后端 limit/offset 参数，添加分页 UI 控件
- 创建可复用的分页组件，统一所有列表页面的分页交互

## Capabilities

### New Capabilities
- `paginated-list-query`: 统一的分页查询模式——后端返回 `{ items, total, limit, offset }` 格式，前端使用统一组件控制翻页
- `pagination-controls`: 可复用的前端分页 UI 组件，支持上一页/下一页、页码显示、每页条数选择

### Modified Capabilities
（无已有 spec 需要修改）

## Impact

- **后端 API**：`GET /sources`、`GET /recipes`、`GET /schedules` 响应格式变更（**BREAKING**）
- **前端页面**：sources-page、recipes-page、schedules-page、crawls-page、jobs-page 需更新
- **前端 API 客户端**：source-api.ts、recipe-api.ts、schedule-api.ts 需更新类型和调用方式
- **前端组件**：新增可复用分页组件
