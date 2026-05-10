## Why

Harvester 已经具备 chunk embedding worker 和 `vector_search` 内核，但公开搜索入口仍只支持关键词标题搜索。现在应把语义检索暴露给 API/CLI，让用户和 agent 能验证 `chunk -> embedding -> vector_search` 的完整闭环，并为后续 LightRAG batch index 提供基础入口。

## What Changes

- 扩展 `GET /items/search`，新增 vector 搜索模式，例如 `mode=vector`。
- vector 模式使用查询文本生成 query embedding，并调用现有 `harvester.search.vector.vector_search`。
- vector 搜索只返回 `embedding_status="ready"` 且有 embedding 的 chunk。
- vector 结果返回 chunk 级可追溯字段：`chunk_id`、`item_version_id`、`content_item_id`、`title`、`text` 或 snippet、`distance`。
- vector 搜索支持 `limit`，并补齐 `source_id`、`topic_watch_id` 过滤。
- 扩展 CLI，支持 `harvester search "<query>" --mode vector`。
- 新增 API、CLI 和集成测试，证明 worker 生成 embedding 后可以通过公开入口搜索到 chunk。
- 本 change 不实现 LightRAG、KG、真实 Qwen embedding 服务或新的数据库 schema。

## Capabilities

### New Capabilities

### Modified Capabilities

- `search-api-cli`: 增加 vector 搜索模式、chunk 级结果契约、CLI mode 参数和 raw-to-vector 公开入口验证。

## Impact

- 修改 `harvester/api/routers/search.py`，扩展请求参数、响应模型和分支逻辑。
- 修改 `harvester/search/vector.py`，如有必要补齐 source/topic 过滤能力。
- 修改 `harvester/cli/main.py` 和搜索 CLI 测试，支持 `--mode vector`。
- 复用 `harvester/adapters/stub_model.py` 生成 query embedding。
- 新增或扩展 `tests/api/test_search.py`、`tests/cli/test_search_cli_http_only.py`、`tests/integration/` 和 `tests/search/test_vector_search.py`。
- 不新增外部依赖，不修改生产数据库 schema。
