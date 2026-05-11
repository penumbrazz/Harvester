## ADDED Requirements

### Requirement: Watch schedule 管理
系统 SHALL 提供持久化 watch schedule，用于描述 source/topic-source 应在何时产生 crawl job。

#### Scenario: 创建 source schedule
- **WHEN** 客户端为 watched source 和 approved recipe 创建 interval schedule
- **THEN** 系统 MUST 保存 schedule，并包含 source、recipe、interval、next run time、status 和唯一 schedule key

#### Scenario: 创建 topic source schedule
- **WHEN** 客户端为 active topic watch 下的 source 创建 interval schedule
- **THEN** 系统 MUST 保存包含 topic watch、source、recipe 和 interval 的 schedule

#### Scenario: 重复 schedule 被拒绝
- **WHEN** 客户端使用相同 topic/source/recipe 组合重复创建 active schedule
- **THEN** 系统 MUST 拒绝重复 schedule 或返回已有 schedule，且不能创建第二条 active schedule

#### Scenario: 未批准 recipe 不能创建 active schedule
- **WHEN** 客户端为未 approved 的 recipe 创建 active schedule
- **THEN** 系统 MUST 拒绝请求，且不能创建 schedule

### Requirement: Scheduler one-shot enqueue
系统 SHALL 提供 one-shot scheduler，把到期的 active watch schedule 转换为 `crawl` job。

#### Scenario: 到期 source schedule 创建 crawl job
- **WHEN** scheduler 运行且存在 `next_run_at <= now` 的 active source schedule
- **THEN** 系统 MUST 创建 `job_type="crawl"` 的 pending job，payload 包含 `source_id`、`recipe_id`、`schedule_id` 和调度窗口

#### Scenario: 到期 topic source schedule 创建 crawl job
- **WHEN** scheduler 运行且存在到期的 active topic source schedule
- **THEN** 系统 MUST 创建 `crawl` job，payload 包含 `topic_watch_id`、`source_id`、`recipe_id`、`schedule_id` 和调度窗口

#### Scenario: 未到期 schedule 不创建 job
- **WHEN** scheduler 运行且 schedule 的 `next_run_at` 晚于当前时间
- **THEN** 系统 MUST 不为该 schedule 创建 crawl job

#### Scenario: enqueue 后推进 next_run_at
- **WHEN** scheduler 成功为 schedule 创建或确认已有当前窗口 crawl job
- **THEN** 系统 MUST 更新该 schedule 的 `last_enqueued_at` 和下一次 `next_run_at`

### Requirement: Scheduler 幂等
系统 SHALL 保证同一 schedule 的同一调度窗口最多创建一个 crawl job。

#### Scenario: 重复运行 scheduler 不重复创建 job
- **WHEN** scheduler 对同一到期 schedule 连续运行两次
- **THEN** 系统 MUST 只保留一个使用相同 idempotency key 的 crawl job

#### Scenario: 并发 scheduler 不重复创建 job
- **WHEN** 两个 scheduler 实例同时处理同一到期 schedule
- **THEN** 系统 MUST 通过数据库唯一约束或等价机制避免重复 crawl job

### Requirement: Topic TTL 调度边界
系统 SHALL 在 Topic Watch 过期后停止为该 topic 创建新的 crawl job。

#### Scenario: 过期 topic 不 enqueue
- **WHEN** scheduler 运行且 schedule 关联的 topic watch `expires_at <= now`
- **THEN** 系统 MUST 不创建 crawl job，并在 scheduler 结果中记录 skipped 计数

#### Scenario: 非 active topic 不 enqueue
- **WHEN** scheduler 运行且 schedule 关联的 topic watch 状态不是 `active`
- **THEN** 系统 MUST 不创建 crawl job

### Requirement: Crawl job worker
系统 SHALL 提供 `crawl` job handler，用于从 job 队列执行公开网页抓取。

#### Scenario: 成功处理 crawl job
- **WHEN** worker 认领 payload 包含有效 `source_id` 和 `recipe_id` 的 `crawl` job
- **THEN** 系统 MUST 调用现有 crawl execution service，创建 crawl run、raw object metadata 和 audit，并将 job 标记为 completed

#### Scenario: Crawl job 携带 topic_watch_id
- **WHEN** worker 处理 payload 包含 `topic_watch_id` 的 `crawl` job
- **THEN** 系统 MUST 将该 topic watch 传递到 crawl run 或下游可追溯 metadata 中

#### Scenario: 可重试 crawl 失败进入 retry
- **WHEN** crawl job 因 adapter、network 或 archive 临时错误失败
- **THEN** 系统 MUST 调用现有 job failure 逻辑，按 retry/dead-letter 机制处理该 job

#### Scenario: 永久 crawl 失败不无限重试
- **WHEN** crawl job 因 fetch policy 拒绝、未批准 recipe、高风险 recipe 或缺失实体失败
- **THEN** 系统 MUST 保留失败 crawl run 或诊断错误，并且不能无限重试该 job

### Requirement: Worker CLI job type 选择
系统 SHALL 允许运维入口显式处理 crawl job，同时保持现有 embedding worker 默认行为。

#### Scenario: 默认 worker once 保持 embedding 行为
- **WHEN** 用户运行 `harvester worker once --limit 1` 且未指定 job type
- **THEN** 系统 MUST 保持现有只处理 `embed_chunks` job 的行为

#### Scenario: CLI 处理 crawl job
- **WHEN** 用户运行 crawl worker one-shot 命令或 `harvester worker once --job-type crawl --limit 1`
- **THEN** 系统 MUST 只认领并处理 `crawl` job

#### Scenario: Scheduler CLI one-shot
- **WHEN** 用户运行 scheduler one-shot 命令
- **THEN** 系统 MUST 执行一次 scheduler，并输出 scanned、enqueued、skipped 和 duplicate 计数

### Requirement: Queue status inspection
系统 SHALL 提供基础队列状态查看能力，帮助诊断 scheduler 和 crawl worker。

#### Scenario: 查看 crawl job 队列状态
- **WHEN** 用户请求查看队列状态
- **THEN** 系统 MUST 返回按 job type 和 status 聚合的 job 数量

#### Scenario: 队列状态不暴露 raw payload
- **WHEN** 系统返回队列状态
- **THEN** 响应 MUST 不包含 raw payload 内容
