## 1. Adapter 配置与依赖

- [x] 1.1 先写 `tests/adapters/test_embedding_settings.py`，覆盖默认 stub、显式 qwen、缺少 Qwen base URL、模型名、维度和 timeout 配置。
- [x] 1.2 将 `httpx` 提升为运行时依赖，确保生产 CLI/API/worker 可用。
- [x] 1.3 新增 `EmbeddingSettings` 和 `create_embedding_adapter()` 工厂，默认返回 `StubModelAdapter`。
- [x] 1.4 运行 `uv run pytest tests/adapters/test_embedding_settings.py -q` 并修复失败。

## 2. Qwen Adapter

- [x] 2.1 先写 `tests/adapters/test_qwen_embedding.py`，使用 mocked HTTP transport 覆盖请求 URL、model/input body、成功解析、timeout、HTTP 错误、缺失 embedding、维度不匹配和非有限数值。
- [x] 2.2 实现 `harvester/adapters/qwen_embedding.py`，提供 `embed(text: str) -> list[float]`。
- [x] 2.3 确保 adapter 不记录完整输入文本或 raw payload 内容到日志。
- [x] 2.4 运行 `uv run pytest tests/adapters/test_qwen_embedding.py tests/adapters/test_stub_model.py -q` 并修复失败。

## 3. Embedding Worker 接入

- [x] 3.1 先扩展 `tests/workers/test_daemon.py` 和 `tests/cli/test_worker_cli.py`，覆盖 worker CLI/daemon 使用 adapter factory，默认仍为 stub，配置 qwen 时使用 Qwen adapter。
- [x] 3.2 更新 worker CLI `once` 和 `run`，通过 `EmbeddingSettings` / factory 创建 adapter 和 model name。
- [x] 3.3 保持 `process_embed_chunks_job` 的 1536 维校验、ready skip、retry/dead-letter 行为不变。
- [x] 3.4 运行 `uv run pytest tests/workers/test_daemon.py tests/workers/test_embedding_handler.py tests/cli/test_worker_cli.py -q` 并修复失败。

## 4. Vector Search Query Adapter

- [x] 4.1 先扩展 `tests/api/test_search.py` 或新增 `tests/api/test_vector_query_adapter.py`，覆盖 vector search 使用配置化 adapter 而不是硬编码 `StubModelAdapter`。
- [x] 4.2 覆盖 query embedding 失败时 API 返回可诊断错误，且不能返回空结果。
- [x] 4.3 更新 `harvester/api/routers/search.py`，通过 adapter factory 生成 query embedding。
- [x] 4.4 确保 keyword search 行为和 CLI HTTP-only 行为不变。
- [x] 4.5 运行 `uv run pytest tests/api/test_search.py tests/cli/test_search_cli_http_only.py -q` 并修复失败。

## 5. 配置化闭环验证

- [x] 5.1 新增或扩展集成测试，使用同一个 mocked/configured adapter 完成 `embed_chunks` worker -> chunk ready -> `GET /items/search?mode=vector` 查询闭环。
- [x] 5.2 保留现有 stub 集成测试，确保未配置 Qwen 时 CI 仍离线通过。
- [x] 5.3 新增可选 live Qwen smoke 测试，只有显式设置 live 环境变量时才调用真实本地模型服务。
- [x] 5.4 运行 `uv run pytest tests/integration/test_vector_search_api_pipeline.py -q` 并修复失败。

## 6. 文档与部署配置

- [x] 6.1 更新 `.env.example`，增加 `HARVESTER_EMBEDDING_ADAPTER`、`HARVESTER_EMBEDDING_MODEL`、`HARVESTER_EMBEDDING_DIMENSION`、`HARVESTER_QWEN_EMBEDDING_BASE_URL` 和 timeout 示例。
- [x] 6.2 更新 README，说明 stub 默认行为、切换 Qwen adapter 的步骤和 live smoke 命令。
- [x] 6.3 确认文档继续强调 raw payload 不做 embedding，embedding 只从 `item_version -> chunk` 开始。
- [x] 6.4 如 Docker Compose worker 需要环境变量，更新 compose 和 smoke 测试。
- [x] 6.5 运行 `uv run pytest tests/deploy -q` 并修复失败。

## 7. 最终验证

- [x] 7.1 运行相关测试：`uv run pytest tests/adapters tests/workers tests/api/test_search.py tests/cli/test_worker_cli.py tests/integration/test_vector_search_api_pipeline.py -q`。
- [x] 7.2 运行全量测试：`uv run pytest -q`。
- [x] 7.3 手动确认 `openspec status --change add-qwen-embedding-adapter` 显示 apply-ready。
