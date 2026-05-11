## ADDED Requirements

### Requirement: Dashboard summary
系统 SHALL 提供管理控制台仪表盘摘要，聚合 Harvester 运行状态。

#### Scenario: Load dashboard summary
- **WHEN** 前端请求 dashboard summary
- **THEN** 系统 MUST 返回 source、crawl run、job、content item、failure 和 audit event 的关键计数

#### Scenario: Summary excludes raw payload
- **WHEN** dashboard summary 返回 crawl 或 raw object 相关指标
- **THEN** 响应 MUST NOT 包含 raw HTML、API payload 或 archive 文件内容

### Requirement: Crawl run observability
系统 SHALL 提供 crawl run 列表和手动触发入口。

#### Scenario: List crawl runs
- **WHEN** 用户打开爬取任务页面
- **THEN** 系统 MUST 展示 crawl run ID、source、recipe、状态、HTTP 状态、开始/完成时间、raw object ID 和错误消息

#### Scenario: Trigger crawl run
- **WHEN** 用户选择 source 和 approved recipe 后发起爬取
- **THEN** 前端 MUST 调用真实 `POST /crawl/run` 并展示返回的 crawl run 状态

### Requirement: Job queue observability
系统 SHALL 提供 job queue 聚合和列表视图。

#### Scenario: View job list
- **WHEN** 用户打开作业队列页面
- **THEN** 系统 MUST 展示 job 类型、状态、优先级、attempts、run_after、locked_by、lane、source 和最近错误

#### Scenario: Filter jobs
- **WHEN** 用户按 job 类型、状态或 lane 筛选
- **THEN** 页面 MUST 只展示匹配的 jobs

### Requirement: Recent failures panel
系统 SHALL 在运维页面展示最近 crawl 和 job 失败。

#### Scenario: Load recent failures
- **WHEN** 用户打开 dashboard 或失败区域
- **THEN** 前端 MUST 调用真实 failure API 并展示失败实体 ID、状态、错误信息和创建时间
