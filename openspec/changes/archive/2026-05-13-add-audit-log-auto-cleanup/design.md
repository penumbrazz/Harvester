## Context

Harvester 当前通过 `audit_events` 表记录状态变更、拒绝操作和重要 pipeline 决策，并已有 `created_at` 索引支持按时间查询。审计事件是控制平面的近期解释层，但它不是 raw evidence、content item 或 job 历史的长期存储来源；如果无限增长，会让个人 home lab 数据库持续膨胀。

现有后台能力包含 scheduler daemon、crawl worker、embedding worker 和可复用的 job repository。`start.sh` 已通过 `HARVESTER_START_DAEMONS=1` 显式启动 scheduler 与 crawl worker，因此审计清理应复用现有 daemon 生命周期，不新增默认常驻进程。

## Goals / Non-Goals

**Goals:**

- 默认只保留最近 7 天的 audit events。
- 支持通过环境变量覆盖保留天数。
- 提供独立、可测试的审计清理服务，按 `audit_events.created_at` cutoff 删除过期记录。
- 将自动清理接入现有 daemon 路径，使启用后台进程后无需人工触发。
- 确保清理不会级联删除 source、recipe、schedule、crawl run、job、raw object、content item 或 chunk 等非审计数据。

**Non-Goals:**

- 不修改 audit event 的写入契约；状态变更和 pipeline 决策仍按现有路径写入 audit。
- 不实现审计归档到外部存储，也不提供长期合规审计保留。
- 不删除 raw payload、raw metadata 或 content/search 数据；raw payload retention 继续由既有 raw retention 逻辑负责。
- 不新增前端页面或更改审计日志列表 UI。

## Decisions

1. **使用独立的 audit retention 模块，而不是把删除逻辑放进 router。**
   - 原因：清理是后台维护任务，不属于审计查询 API 的职责。独立模块可以被 scheduler、测试和未来运维 API 复用。
   - 替代方案：在 `GET /audit/events` 前顺带清理。实现简单，但读请求产生写副作用，且会让测试和运维行为不可预测。

2. **默认配置为 `HARVESTER_AUDIT_RETENTION_DAYS=7`。**
   - 原因：与用户需求一致，也和 raw payload 默认短保留窗口保持一致。配置读取应集中在新 settings/dataclass 或 audit retention 模块入口，避免在多处解析环境变量。
   - 替代方案：硬编码 7 天。短期更少代码，但无法支持本地实验或临时延长审计窗口。

3. **按 `created_at < cutoff` 删除 audit events，并返回清理统计。**
   - 原因：`audit_events.created_at` 已有索引，cutoff 语义清晰，可直接覆盖边界测试。返回值至少包含 `deleted_count`、`cutoff` 和 `retention_days`，便于 daemon 日志、API/CLI 输出和测试断言。
   - 替代方案：逐行加载 ORM 对象后删除。更容易写，但对大量审计日志低效。

4. **自动清理接入 scheduler daemon 的维护阶段。**
   - 原因：scheduler daemon 已是周期性后台协调者，并由 `HARVESTER_START_DAEMONS=1` 控制启动。把 audit cleanup 放入 scheduler loop 可避免新增服务和部署配置。
   - 替代方案：新增 `audit_cleanup` job type 并由 worker 消费。这能统一 job 可见性，但需要新增 job enqueue、worker lane、CLI job-type 和部署健康检查，超出当前需求的必要复杂度。

5. **清理失败只记录错误并允许下一轮重试。**
   - 原因：审计清理是维护任务，不应阻断 scheduler 入队 crawl job。失败后下一轮 daemon 仍可再次尝试。
   - 替代方案：清理失败直接让 scheduler 轮次失败。更显眼，但会把非关键维护故障放大为采集调度故障。

## Risks / Trade-offs

- [Risk] 7 天窗口可能短于某些排障周期。→ Mitigation：通过 `HARVESTER_AUDIT_RETENTION_DAYS` 覆盖，并在 `.env.example` 或部署文档中说明默认值。
- [Risk] scheduler daemon 每轮执行清理会产生无意义 DELETE。→ Mitigation：实现 daemon 内部节流，例如默认 24 小时运行一次；手动调用清理服务不受节流影响。
- [Risk] 删除 audit events 会削弱旧状态变更的解释能力。→ Mitigation：长期业务实体、crawl run、job、raw metadata 和 content 数据仍保留；spec 明确 audit events 是短保留控制面日志。
- [Risk] 大量过期事件一次删除可能造成锁或事务压力。→ Mitigation：按 cutoff 删除并复用 `created_at` 索引；如实现时发现数据量较大，可在清理函数中支持批量 limit。

## Migration Plan

1. 先写审计清理单元测试和 scheduler daemon 集成测试，覆盖默认 7 天、环境变量覆盖、cutoff 边界、非审计数据不受影响和清理失败不阻断 scheduler。
2. 实现 audit retention 配置和清理服务。
3. 将 scheduler daemon 接入节流后的清理调用，并记录清理统计。
4. 如部署配置或 `.env.example` 已列出 Harvester env vars，补充 `HARVESTER_AUDIT_RETENTION_DAYS`。
5. 回滚时可禁用 scheduler daemon 或将保留天数设置为较大值；已删除的 audit events 不恢复，但业务数据不受影响。

## Open Questions

- 是否需要在后续 change 中提供审计日志导出或长期归档能力，取决于 home lab 是否出现超过 7 天的审计追溯需求。
