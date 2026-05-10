## Why

Harvester 已经会为 chunk 创建 `embed_chunks` job，也具备 pgvector-ready `chunks.embedding` 字段和向量搜索函数，但还没有 worker 消费这些 job 并写回 embedding。搜索 API/CLI 已经完成后，下一步应补齐 `item_version -> chunk -> embedding -> vector_search` 的实际执行闭环，为后续 LightRAG 和语义检索打基础。

## What Changes

- 新增 embedding worker daemon，能够认领并处理 `embed_chunks` job。
- 新增单个 embedding job 处理逻辑：读取 job payload 中的 `chunk_id`，读取 chunk text，调用 model adapter，写回 `chunks.embedding`、`embedding_model` 和 `embedding_status`。
- 成功时标记 job completed；失败时调用现有 retry/dead-letter 机制。
- 提供 one-shot 执行模式，便于测试、手动运行和 Docker smoke。
- 提供 loop 执行模式，供 Docker Compose worker 长时间消费队列。
- 更新 worker CLI/入口和 Docker Compose worker command，使 compose 中的 worker 真正运行 worker daemon。
- 使用现有 `StubModelAdapter` 作为第一版 deterministic embedding adapter，不引入外部模型服务依赖。
- 本 change 不实现 LightRAG、KG、真实本地 Qwen embedding 服务或向量搜索 API。

## Capabilities

### New Capabilities

- `embedding-worker-daemon`: 后台 worker 认领 `embed_chunks` job，生成 chunk embedding，更新 chunk 状态，并复用 job retry/dead-letter 机制。

### Modified Capabilities

## Impact

- 新增 worker 模块，例如 `harvester/workers/embedding.py` 和 `harvester/workers/daemon.py`。
- 扩展 CLI，例如新增 `harvester worker run` / `harvester worker once` 命令。
- 更新 `docker-compose.yml` 中 worker service 的 command 和 healthcheck。
- 复用 `harvester/jobs/repository.py`、`harvester/adapters/stub_model.py`、`harvester/db/models.py`。
- 新增 worker 单元测试、job 集成测试和 deploy 配置测试。
- 不修改数据库 schema，不新增外部依赖。
