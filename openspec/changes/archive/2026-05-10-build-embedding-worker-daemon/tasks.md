## 1. Embed Job Handler 测试

- [x] 1.1 创建 `tests/workers/test_embedding_handler.py`，覆盖有效 `embed_chunks` job 会读取 chunk text、写入 1536 维 embedding、`embedding_model` 和 `embedding_status="ready"`。
- [x] 1.2 覆盖 `embedding_status="ready"` 的 chunk 不重复调用 adapter，job 仍标记 completed。
- [x] 1.3 覆盖 adapter 抛异常时调用 `fail_job`，可重试失败保持 chunk `embedding_status="pending"`。
- [x] 1.4 覆盖缺失或非法 `chunk_id` payload 会失败 job，并记录可诊断错误。
- [x] 1.5 覆盖最后一次尝试失败会将对应 chunk 标记为 `embedding_status="failed"`。

## 2. Embed Job Handler 实现

- [x] 2.1 新增 `harvester/workers/` 包和 `harvester/workers/embedding.py`。
- [x] 2.2 实现 `process_embed_chunks_job(session, job, adapter, model_name)`，处理 payload 校验、chunk 加载、ready 跳过、adapter 调用和 chunk 写回。
- [x] 2.3 在 handler 中复用 `complete_job` 和 `fail_job`，保证事务边界清晰。
- [x] 2.4 运行 `uv run pytest tests/workers/test_embedding_handler.py -q` 并确认通过。

## 3. Worker Daemon 测试

- [x] 3.1 创建 `tests/workers/test_daemon.py`，覆盖 one-shot worker 只通过 `claim_next_jobs(..., lanes=["embed_chunks"])` 认领 embedding job。
- [x] 3.2 覆盖 one-shot 空队列时返回 claimed/completed/failed 计数为 0。
- [x] 3.3 覆盖 one-shot `limit` 最多处理指定数量的 job。
- [x] 3.4 覆盖 loop worker 按 poll interval 重复调用 one-shot 逻辑，并可通过测试 stop 条件退出。

## 4. Worker Daemon 实现

- [x] 4.1 新增 `harvester/workers/daemon.py`，实现 `run_once(...)`，返回处理统计。
- [x] 4.2 实现 `run_loop(...)`，支持 `poll_interval`、`limit`、`worker_id` 和测试用 stop 条件。
- [x] 4.3 为 worker id 提供稳定默认值，例如主机名 + 进程 id。
- [x] 4.4 运行 `uv run pytest tests/workers/test_daemon.py -q` 并确认通过。

## 5. CLI 和 Compose 测试

- [x] 5.1 创建 `tests/cli/test_worker_cli.py`，覆盖 `harvester worker once --limit 1` 调用 one-shot worker 并输出统计。
- [x] 5.2 覆盖 `harvester worker run --poll-interval 5` 调用 loop worker 并传递轮询参数。
- [x] 5.3 扩展 `tests/deploy/test_compose_config.py`，断言 worker service command 启动真实 worker daemon。
- [x] 5.4 扩展 compose 测试，断言 worker healthcheck 匹配新的 worker 进程入口。

## 6. CLI 和 Compose 实现

- [x] 6.1 在 `harvester/cli/main.py` 增加 `worker` Typer 子命令组。
- [x] 6.2 实现 `worker once` 和 `worker run` 命令，复用 `DatabaseSettings` 创建 session 并调用 worker daemon。
- [x] 6.3 更新 `docker-compose.yml` worker command 为 `uv run harvester worker run` 或等价入口。
- [x] 6.4 更新 worker healthcheck，匹配新的 worker 进程。
- [x] 6.5 运行 `uv run pytest tests/cli/test_worker_cli.py tests/deploy/test_compose_config.py -q` 并确认通过。

## 7. 集成和向量搜索验证

- [x] 7.1 创建 `tests/integration/test_embedding_worker_pipeline.py`，构造 pending chunk 和 `embed_chunks` job，运行 one-shot worker。
- [x] 7.2 验证 worker 成功后 job completed，chunk `embedding_status="ready"` 且 embedding 非空。
- [x] 7.3 验证成功 embedding 的 chunk 可被现有 `vector_search` 返回。
- [x] 7.4 运行 `uv run pytest tests/integration/test_embedding_worker_pipeline.py tests/search/test_vector_search.py -q` 并确认通过。

## 8. 全量验证

- [x] 8.1 运行 `uv run pytest tests/workers/ tests/cli/test_worker_cli.py tests/deploy/test_compose_config.py tests/integration/test_embedding_worker_pipeline.py -q` 并确认通过。
- [x] 8.2 运行 `uv run pytest -q` 并确认全量测试通过。
- [x] 8.3 运行 `openspec validate build-embedding-worker-daemon --type change --strict` 并确认通过。
