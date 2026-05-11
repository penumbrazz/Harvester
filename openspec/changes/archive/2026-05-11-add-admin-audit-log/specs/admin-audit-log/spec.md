## ADDED Requirements

### Requirement: Audit event list API
系统 SHALL 提供 audit event 列表 API，用于管理控制台查询审计事件。

#### Scenario: List audit events
- **WHEN** 前端携带有效 API token 请求 audit events
- **THEN** 系统 MUST 返回事件 ID、actor、action、entity type、entity ID、before/after state 摘要、reason 和 created_at

#### Scenario: Filter audit events
- **WHEN** 用户按 entity type、entity ID、action、actor 或时间范围筛选
- **THEN** API 或前端 MUST 只展示匹配条件的 audit events

### Requirement: Audit timeline UI
系统 SHALL 在管理控制台以时间线方式展示审计事件。

#### Scenario: Render audit timeline
- **WHEN** 用户打开审计日志页面
- **THEN** 页面 MUST 按 created_at 倒序展示 audit event 时间线

#### Scenario: Load more audit events
- **WHEN** 用户点击加载更多
- **THEN** 页面 MUST 请求下一页真实 audit events 并追加到时间线

### Requirement: Entity traceability
系统 SHALL 支持按实体查看相关审计事件。

#### Scenario: Filter by entity
- **WHEN** 用户使用 entity type 和 entity ID 过滤审计日志
- **THEN** 页面 MUST 只展示该实体相关的状态变化、拒绝操作和管线事件

### Requirement: Audit UI excludes raw payload
系统 SHALL 确保审计日志页面不泄漏 raw payload。

#### Scenario: Display audit event details
- **WHEN** 审计日志展示 before_state、after_state 或 reason
- **THEN** UI MUST NOT 展示 raw HTML、API payload 或 archive 文件内容
