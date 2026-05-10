## ADDED Requirements

### Requirement: Embed chunks job handler
系统 SHALL 提供 `embed_chunks` job handler，用于将 chunk text 转换为 embedding 并写回 `chunks` 表。

#### Scenario: 成功处理 chunk embedding
- **WHEN** worker 收到 payload 包含有效 `chunk_id` 的 `embed_chunks` job
- **THEN** 系统 MUST 读取对应 chunk 的 `text`，生成 1536 维 embedding，并写入 `chunks.embedding`

#### Scenario: 写入 embedding 状态
- **WHEN** chunk embedding 成功生成并保存
- **THEN** 系统 MUST 将该 chunk 的 `embedding_status` 更新为 `ready`，并写入非空 `embedding_model`

#### Scenario: 已 ready 的 chunk 不重复 embedding
- **WHEN** worker 收到的 job 指向 `embedding_status="ready"` 的 chunk
- **THEN** 系统 MUST 不重新生成 embedding，并将 job 标记为 completed

### Requirement: Job claim and completion
系统 SHALL 使用现有 Postgres job lease 机制认领和完成 `embed_chunks` job。

#### Scenario: One-shot 认领 pending job
- **WHEN** 运行 one-shot worker 且存在可运行的 `embed_chunks` pending job
- **THEN** 系统 MUST 通过 `claim_next_jobs` 认领 job，并将其状态置为 running

#### Scenario: 成功 job 标记 completed
- **WHEN** `embed_chunks` job 成功处理
- **THEN** 系统 MUST 调用 job completion 逻辑，将 job 状态标记为 completed 并释放 lease

#### Scenario: 只认领 embedding job
- **WHEN** 队列中同时存在 `embed_chunks` 和其他 job type
- **THEN** embedding worker MUST 只认领和处理 `embed_chunks` job

### Requirement: Failure and retry behavior
系统 SHALL 在 embedding job 失败时复用现有 retry/dead-letter 机制。

#### Scenario: Adapter 失败触发 job failure
- **WHEN** embedding adapter 在处理 chunk 时抛出异常
- **THEN** 系统 MUST 调用 `fail_job` 记录错误并按现有 retry 机制处理该 job

#### Scenario: 可重试失败保留 chunk pending
- **WHEN** `embed_chunks` job 失败但仍可重试
- **THEN** 系统 MUST 保持 chunk 的 `embedding_status` 为 `pending`

#### Scenario: 终止失败标记 chunk failed
- **WHEN** `embed_chunks` job 已耗尽可用尝试或 payload 永久无效
- **THEN** 系统 MUST 将对应 chunk 的 `embedding_status` 更新为 `failed`

#### Scenario: 缺失 chunk 失败
- **WHEN** job payload 中的 `chunk_id` 不存在或无法解析
- **THEN** 系统 MUST 将 job 标记为失败，并记录可诊断的错误信息

### Requirement: Worker execution modes
系统 SHALL 提供 one-shot 和 loop 两种 worker 执行模式。

#### Scenario: One-shot 空队列返回零处理
- **WHEN** 运行 one-shot worker 且没有可运行的 `embed_chunks` job
- **THEN** 系统 MUST 正常退出，并报告 claimed/completed/failed 计数为 0

#### Scenario: One-shot 处理数量上限
- **WHEN** 运行 one-shot worker 并指定 `limit=2`
- **THEN** 系统 MUST 单次最多认领并处理 2 个 `embed_chunks` job

#### Scenario: Loop worker 持续轮询
- **WHEN** 运行 loop worker
- **THEN** 系统 MUST 按配置的 poll interval 重复调用 one-shot 处理逻辑

### Requirement: Worker CLI
系统 SHALL 通过 CLI 暴露 worker 运行入口。

#### Scenario: CLI one-shot 入口
- **WHEN** 用户运行 `harvester worker once --limit 1`
- **THEN** CLI MUST 执行一次 embedding worker 处理，并输出处理统计

#### Scenario: CLI loop 入口
- **WHEN** 用户运行 `harvester worker run --poll-interval 5`
- **THEN** CLI MUST 启动 loop worker，并使用指定轮询间隔

### Requirement: Docker Compose worker
系统 SHALL 让 Docker Compose worker service 运行真实 worker daemon。

#### Scenario: Compose worker command
- **WHEN** 检查 `docker-compose.yml`
- **THEN** worker service command MUST 启动 `harvester worker run` 或等价 worker daemon 入口

#### Scenario: Compose worker healthcheck
- **WHEN** 检查 `docker-compose.yml`
- **THEN** worker service MUST 保留 healthcheck，且 healthcheck MUST 匹配新的 worker 进程入口

### Requirement: Vector search readiness
系统 SHALL 通过测试验证成功 embedding 的 chunk 可被现有 vector search 查询。

#### Scenario: Embedded chunk 可被 vector search 返回
- **WHEN** worker 成功将 chunk 标记为 `ready` 并写入 embedding
- **THEN** 调用现有 vector search MUST 能返回该 chunk
