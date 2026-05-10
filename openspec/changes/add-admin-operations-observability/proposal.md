## Why

Harvester 已有 watch scheduler、crawl worker、队列和失败查询，但运维时仍难以从一个视图回答“系统是否在跑、哪里堵住、最近失败是什么”。需要把 dashboard、crawl runs、jobs 和 failures 做成真实观测界面。

## What Changes

- 新增 dashboard summary API，聚合 sources、crawl runs、jobs、content items、failures、audit events 的关键计数。
- 新增 crawl run 列表 API，支持按状态、source、时间排序和分页查看 crawl run。
- 扩展 job queue read API，从仅聚合计数扩展到 jobs 列表视图，支持状态、类型、lane、source 筛选。
- 复用 `/failures/recent`，在前端展示最近 crawl/job 失败原因。
- 新增管理控制台仪表盘、爬取任务页和作业队列页，支持手动触发 crawl run。
- 不在本 change 中实现 retry/cancel/force retry 等破坏性或复杂队列操作，除非已有安全后端 API。

## Capabilities

### New Capabilities

- `admin-operations-observability`: 管理控制台的 dashboard、crawl run、job queue 和 recent failure 观测能力。

### Modified Capabilities

- 无。

## Impact

- 后端新增 dashboard、crawl run list、job list read APIs，继续避免暴露 raw payload。
- 前端新增 dashboard/runs/jobs 页面、筛选控件、状态展示和 crawl 触发表单。
- 测试新增 API 查询测试、聚合测试和真实 HTTP E2E。
- 依赖 `add-admin-console-foundation`；可与 `add-admin-source-management` 之后串行实现以复用 source selector。
