## Context

Harvester 已有调度器、crawl worker、job 队列和失败查询，但缺少统一观测视图。这个 change 负责“系统正在发生什么”：dashboard、crawl run 列表、job 列表、失败摘要和手动 crawl 触发。

## Goals / Non-Goals

**Goals:**

- 提供 dashboard summary API，聚合关键运行指标。
- 提供 crawl run 和 job queue 的列表 read API，支持分页和筛选。
- 前端实现 dashboard、爬取任务页、作业队列页和最近失败展示。
- 手动触发 crawl 继续调用现有 `POST /crawl/run`。

**Non-Goals:**

- 不实现 job cancel、retry、force retry 或死信恢复。
- 不展示 raw payload 或 archive 文件内容。
- 不做实时 websocket；第一版使用刷新/重新拉取。

## Decisions

1. **dashboard 使用后端聚合 API。**
   - 原因：计数定义应由后端统一，避免前端多次拉列表后自行推导。
   - 替代方案：前端并发调用多个 API 计算。简单但口径容易漂移。

2. **crawl run/job 使用列表 API 而非只返回聚合。**
   - 原因：运维排查需要看到具体 run/job、错误、锁定者、attempts 和时间。
   - 替代方案：只展示 `/queue/status`。无法定位单个问题。

3. **第一版采用手动刷新。**
   - 原因：系统当前 worker/scheduler 是 one-shot/daemon 混合，轮询已经足够。
   - 替代方案：SSE/WebSocket。复杂度较高，后续可另立 change。

## Risks / Trade-offs

- [Risk] 聚合查询影响数据库。→ Mitigation: 限制时间窗口、分页和字段，必要时添加索引。
- [Risk] “运行中”状态可能因 worker 崩溃而过期。→ Mitigation: 显示 locked_until/started_at 等上下文，不隐藏异常状态。
- [Risk] 手动 crawl 表单需要 source/recipe 数据。→ Mitigation: 可依赖 source/recipe change；如果缺失，先用 ID 输入降级。
