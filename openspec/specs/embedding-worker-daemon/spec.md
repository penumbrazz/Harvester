## ADDED Requirements

### Requirement: Embed chunks job handler
系统 SHALL 提供 `embed_chunks` job handler，用于通过配置化 embedding adapter 将 chunk text 转换为 embedding 并写回 `chunks` 表。

#### Scenario: 成功处理 chunk embedding
- **WHEN** worker 收到 payload 包含有效 `chunk_id` 的 `embed_chunks` job
- **THEN** 系统 MUST 读取对应 chunk 的 `text`，使用配置化 embedding adapter 生成 1536 维 embedding，并写入 `chunks.embedding`

#### Scenario: 写入 embedding 状态
- **WHEN** chunk embedding 成功生成并保存
- **THEN** 系统 MUST 将该 chunk 的 `embedding_status` 更新为 `ready`，并写入非空 `embedding_model`

#### Scenario: 已 ready 的 chunk 不重复 embedding
- **WHEN** worker 收到的 job 指向 `embedding_status="ready"` 的 chunk
- **THEN** 系统 MUST 不重新生成 embedding，并将 job 标记为 completed

#### Scenario: Stub adapter 仍可用于测试
- **WHEN** worker 使用 deterministic stub adapter 处理 `embed_chunks` job
- **THEN** 系统 MUST 保持现有离线测试行为，并生成 1536 维 deterministic embedding

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
系统 SHALL 通过 CLI 暴露 worker 运行入口，并使用配置化 embedding adapter。

#### Scenario: CLI one-shot 入口
- **WHEN** 用户运行 `harvester worker once --limit 1`
- **THEN** CLI MUST 根据 embedding settings 创建 adapter，执行一次 embedding worker 处理，并输出处理统计

#### Scenario: CLI loop 入口
- **WHEN** 用户运行 `harvester worker run --poll-interval 5`
- **THEN** CLI MUST 根据 embedding settings 创建 adapter，启动 loop worker，并使用指定轮询间隔

#### Scenario: CLI 配置为 Qwen adapter
- **WHEN** 用户运行 worker CLI 且 `HARVESTER_EMBEDDING_ADAPTER=qwen`
- **THEN** CLI MUST 使用 Qwen embedding adapter 处理 chunk embedding

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

### Requirement: Embedding worker isolation with scheduler daemons
系统 SHALL 在新增 scheduler daemon 和 crawl worker daemon 后保持 embedding worker 的默认隔离语义。

#### Scenario: 默认 worker run 只处理 embedding job
- **WHEN** 用户运行 `harvester worker run` 且没有指定 `--job-type`
- **THEN** 系统 MUST 只认领和处理 `embed_chunks` job，并保持 `crawl` job 与 `extract` job 不变

#### Scenario: 默认 worker once 只处理 embedding job
- **WHEN** 用户运行 `harvester worker once` 且没有指定 `--job-type`
- **THEN** 系统 MUST 只执行 embedding worker one-shot 逻辑，并保持 `crawl` job 与 `extract` job 不变

#### Scenario: Compose worker service 保持 embedding worker
- **WHEN** 检查 `docker-compose.yml` 中现有 `worker` service
- **THEN** 该 service MUST 继续运行默认 embedding worker daemon，且不能改为消费所有 job type 的通用 worker

#### Scenario: Crawl worker 不初始化 embedding adapter
- **WHEN** 用户运行 `harvester worker run --job-type crawl`
- **THEN** 系统 MUST 启动 crawl worker daemon，且不能要求配置或初始化 embedding adapter

#### Scenario: Extract job 不被新增 daemon 误消费
- **WHEN** 队列中存在 `extract` job，并且只启动 scheduler daemon、crawl worker daemon 和默认 embedding worker
- **THEN** `extract` job MUST 保持 pending，除非用户显式启动对应 extract worker 入口
