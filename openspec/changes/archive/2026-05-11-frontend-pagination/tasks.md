## 1. 后端 API 分页改造

- [x] 1.1 创建统一分页响应模型 `PaginatedResponse[T]`（包含 items、total、limit、offset 字段）
- [x] 1.2 改造 `GET /sources`：添加 limit/offset 参数，返回分页响应格式
- [x] 1.3 改造 `GET /recipes`：添加 limit/offset 参数，返回分页响应格式
- [x] 1.4 改造 `GET /schedules`：添加 limit/offset 参数，返回分页响应格式
- [x] 1.5 扩展 `GET /crawl/runs` 响应：在 CrawlRunListResponse 中添加 limit 和 offset 字段
- [x] 1.6 扩展 `GET /queue/jobs` 响应：在 JobListResponse 中添加 limit 和 offset 字段
- [x] 1.7 为所有改造的后端端点编写/更新测试

## 2. 前端可复用分页组件

- [x] 2.1 创建 `PaginationControls` 组件（接受 total、offset、pageSize、onPageChange props）
- [x] 2.2 为 PaginationControls 编写测试

## 3. 前端 API 客户端更新

- [x] 3.1 更新 `source-api.ts`：listSources 接受 limit/offset 参数，返回分页响应类型
- [x] 3.2 更新 `recipe-api.ts`：listRecipes 接受 limit/offset 参数，返回分页响应类型
- [x] 3.3 更新 `schedule-api.ts`：listSchedules 接受 limit/offset 参数，返回分页响应类型
- [x] 3.4 更新 `observability-api.ts` 中的 CrawlRunListResponse 和 JobListResponse 类型，添加 limit 和 offset 字段

## 4. 前端页面集成分页

- [x] 4.1 Sources 页面：添加 offset state 和 PaginationControls 组件
- [x] 4.2 Recipes 页面：添加 offset state 和 PaginationControls 组件
- [x] 4.3 Schedules 页面：添加 offset state 和 PaginationControls 组件
- [x] 4.4 Crawls 页面：添加 offset state 和 PaginationControls，传递 limit/offset 给 API
- [x] 4.5 Jobs 页面：添加 offset state 和 PaginationControls，传递 limit/offset 给 API
- [x] 4.6 Content Library 页面：用共享 PaginationControls 替换内联分页 UI

## 5. 验证

- [x] 5.1 运行后端测试确保所有 API 变更正确
- [x] 5.2 启动前后端，手动验证各页面分页功能
