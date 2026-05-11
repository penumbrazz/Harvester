## Context

AuditEvent 已经记录状态变更、拒绝操作和管线决策，但没有查询 API 和 UI。审计日志页面是 Harvester 控制面的解释层，帮助用户理解某个 source、crawl run、job 或 recipe 为什么变成当前状态。

## Goals / Non-Goals

**Goals:**

- 新增 audit event list API，支持分页和筛选。
- 前端实现审计日志时间线、筛选、加载更多和状态摘要展示。
- 保留从其他页面跳转到 entity-specific audit 视图的接口设计。
- 不暴露 raw payload，只展示 metadata 和状态变化。

**Non-Goals:**

- 不实现审计事件编辑或删除。
- 不实现长期归档、导出 CSV 或全文搜索。
- 不实现 raw evidence diff。

## Decisions

1. **新增独立 audit router。**
   - 原因：audit 是跨实体能力，不应塞进 failures 或 sources router。
   - 替代方案：复用 `/failures/recent`。只能覆盖失败，不能解释正常状态变化。

2. **before/after state 以摘要方式展示。**
   - 原因：JSONB 可能结构不统一，摘要更适合时间线。
   - 替代方案：完整 JSON 默认展开。信息噪音大，移动端体验差。

3. **分页使用 limit/offset 或 cursor，但第一版保持简单。**
   - 原因：数据量初期可控，与现有 search offset 风格一致。
   - 替代方案：cursor-only。更适合大规模，但实现成本更高。

## Risks / Trade-offs

- [Risk] audit after_state 可能包含较大 JSON。→ Mitigation: API 返回摘要字段，并限制完整 JSON 展示长度。
- [Risk] 用户需要跨页面追踪。→ Mitigation: API 支持 entity_type/entity_id 过滤，其他页面后续可链接。
- [Risk] 时间线过长影响性能。→ Mitigation: 默认分页和加载更多。
