## Why

Harvester 的状态机、抓取、队列和策略拒绝都依赖 audit 保持可追溯，但目前没有直接浏览 audit event 的控制台入口。需要一个审计日志页面，让用户能解释状态变化、失败和关键管线决策。

## What Changes

- 新增 audit event 列表 API，支持按 entity type、entity ID、action、actor、时间范围分页筛选。
- 新增审计日志页面，按时间线展示事件，包含 action、entity、before/after state 摘要、reason、actor 和 created_at。
- 从 source、crawl run、job、content item 等页面保留跳转到相关 audit 过滤视图的设计空间。
- 不暴露 raw payload；audit 页面只展示 metadata、状态摘要和原因。
- E2E 覆盖筛选、分页/加载更多、空状态和从测试数据中展示真实 audit event。

## Capabilities

### New Capabilities

- `admin-audit-log`: 管理控制台的审计事件列表、筛选和时间线展示能力。

### Modified Capabilities

- 无。

## Impact

- 后端新增 audit router 或扩展现有 failure/audit 查询模块。
- 前端新增 audit feature 模块、时间线组件、筛选控件和 API 类型。
- 测试新增 audit API 查询测试和真实 HTTP 前端 E2E。
- 依赖 `add-admin-console-foundation`；可在 source/operations/content 页面之后增强交叉跳转。
