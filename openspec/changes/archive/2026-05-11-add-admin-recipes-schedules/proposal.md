## Why

Recipe 和 watch schedule 决定 Harvester 如何抓取、何时抓取，是从“手动触发”走向“持续采集”的关键配置。当前已有创建 recipe、approve recipe、创建 schedule 的 API/CLI，但缺少可浏览、选择、审批和排查的管理界面。

## What Changes

- 新增 recipe 列表 read API，返回名称、executor、risk level、approval status、version、创建/更新时间和必要配置摘要。
- 新增 watch schedule 列表 read API，返回 schedule key、source、topic、recipe、status、interval、next run、last enqueue、priority、lane。
- 新增 recipe/schedule 管理页面，支持列表、筛选、创建 recipe、审批 recipe、创建 source/topic schedule。
- 在新建 crawl run 或 schedule 的流程中使用 approved recipe selector，避免用户手动复制 UUID。
- 不在本 change 中引入登录态、高风险 recipe 沙箱或 browser profile；这些仍属于后续能力。
- 视觉和交互遵循根目录 `DESIGN.md`，表格与表单保持克制、密集但可扫描。

## Capabilities

### New Capabilities

- `admin-recipes-schedules`: 管理控制台的 recipe 审批、recipe 选择和 watch schedule 管理能力。

### Modified Capabilities

- 无。

## Impact

- 后端扩展 `recipes` 和 `schedules` routers，新增 read/list endpoints 和必要过滤参数。
- 前端新增 recipe/schedule feature 模块、列表页面、创建/审批表单和 E2E。
- 测试新增 API 列表/筛选/审批/创建 schedule 覆盖，以及真实 HTTP 前端流程。
- 依赖 `add-admin-console-foundation`；建议在 `add-admin-source-management` 后实现，便于 schedule 表单复用 source selector。
