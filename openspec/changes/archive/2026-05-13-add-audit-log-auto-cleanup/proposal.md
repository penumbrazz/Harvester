## Why

审计事件会随状态变更、抓取、队列和策略决策持续增长，长期无限保留会增加本地 home lab 数据库体积和运维成本。Harvester 需要为审计日志建立默认保留策略，让控制平面在保持近期可追溯性的同时自动清理过期记录。

## What Changes

- 新增审计日志自动清理能力，默认只保留最近 7 天的 audit events。
- 支持通过配置覆盖默认保留天数，便于高审计需求环境延长窗口。
- 新增可由 worker/daemon 或运维命令调用的清理入口，只删除超过保留窗口的 audit events。
- 清理过程必须保留业务实体、raw evidence metadata、content items、jobs、crawl runs 等长期数据，不级联删除非审计记录。
- 清理行为本身需要可诊断，至少提供返回清理数量和 cutoff 时间的结果，便于测试和运维确认。
- 澄清现有管理动作的历史引用要求：业务记录和其历史状态引用仍保留，但 audit events 按审计日志保留策略自动清理。

## Capabilities

### New Capabilities

- `audit-log-retention`: 审计日志保留策略、默认 7 天窗口、自动清理入口和清理安全边界。

### Modified Capabilities

- `admin-management-actions`: 归档、废弃和停用等管理动作仍保留业务历史引用，但 audit events 不再要求无限期保留，而是遵循审计日志保留策略。

## Impact

- 后端：新增 audit retention 配置、清理服务/函数、可调度 job handler 或 daemon 集成点。
- 数据库：复用 `audit_events.created_at` 作为 cutoff 条件，必要时补充索引或迁移以保证清理查询可控。
- API/CLI：如已有运维命令或 worker daemon，可暴露手动触发清理的入口；状态变更仍必须通过 Harvester API。
- 测试：新增后端单元/API 或 job 测试，覆盖默认 7 天、配置覆盖、cutoff 边界和不删除非审计数据。
