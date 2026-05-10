## 1. Vector Search 内核测试

- [x] 1.1 扩展 `tests/search/test_vector_search.py`，覆盖 `source_id` 过滤只返回指定 source 的 ready chunk。
- [x] 1.2 扩展 `tests/search/test_vector_search.py`，覆盖 `topic_watch_id` 过滤只返回指定 topic watch 的 ready chunk。
- [x] 1.3 确认现有测试覆盖 pending chunk、无 embedding chunk 和 dedup collapse；缺口则补测。

## 2. Vector Search 内核实现

- [x] 2.1 修改 `harvester/search/vector.py`，为 `vector_search` 增加 `source_id` 和 `topic_watch_id` 可选参数。
- [x] 2.2 在 SQL 层对 `ContentItem.source_id` 和 `ContentItem.topic_watch_id` 过滤，保持 dedup collapse 后返回 `limit` 条以内。
- [x] 2.3 运行 `uv run pytest tests/search/test_vector_search.py -q` 并确认通过。

## 3. API 测试

- [x] 3.1 扩展 `tests/api/test_search.py`，覆盖 `GET /items/search?q=Python&mode=vector` 使用 query embedding 并返回 vector 结果。
- [x] 3.2 覆盖未传 `mode` 时仍保持 keyword 默认行为。
- [x] 3.3 覆盖非法 `mode` 返回参数错误。
- [x] 3.4 覆盖 vector 空白 query 返回空结果。
- [x] 3.5 覆盖 vector 响应字段包含 `chunk_id`、`item_version_id`、`content_item_id`、`title`、`text`、`distance` 和 `mode`。
- [x] 3.6 覆盖 vector `source_id`、`topic_watch_id`、`limit` 参数透传到搜索层。

## 4. API 实现

- [x] 4.1 修改 `harvester/api/routers/search.py`，新增 `mode` query 参数，取值限制为 `keyword` 或 `vector`。
- [x] 4.2 扩展 response model，支持 keyword 和 vector 两类结果字段，并在结果中标识 `mode`。
- [x] 4.3 在 vector 分支使用 `StubModelAdapter` 为 `q` 生成 1536 维 query embedding。
- [x] 4.4 在 vector 分支调用 `vector_search`，传递 `source_id`、`topic_watch_id` 和 `limit`。
- [x] 4.5 运行 `uv run pytest tests/api/test_search.py -q` 并确认通过。

## 5. CLI 测试

- [x] 5.1 扩展 `tests/cli/test_search_cli_http_only.py`，覆盖 `harvester search "Python" --mode vector` 会向 `/items/search` 传递 `mode=vector`。
- [x] 5.2 覆盖 CLI 透传 vector 模式下的 `--source-id`、`--topic-watch-id` 和 `--limit`。
- [x] 5.3 覆盖 vector 搜索结果输出标题、chunk id、item version id 和 distance。
- [x] 5.4 覆盖 CLI vector 模式不导入数据库 session、model adapter 或 vector search。

## 6. CLI 实现

- [x] 6.1 修改 `harvester/cli/main.py` 的 `search` 命令，新增 `--mode` 参数，默认 `keyword`。
- [x] 6.2 CLI 将 `mode` 和现有过滤参数一起作为 HTTP query params 传给 API。
- [x] 6.3 CLI 按 `mode` 格式化输出：keyword 输出 item/version/source，vector 输出 chunk/version/distance。
- [x] 6.4 运行 `uv run pytest tests/cli/test_search_cli_http_only.py -q` 并确认通过。

## 7. 集成验证

- [x] 7.1 新增或扩展 `tests/integration/test_vector_search_api_pipeline.py`，构造 item/version/chunk 和 `embed_chunks` job。
- [x] 7.2 运行 embedding worker one-shot，使 chunk 变为 `embedding_status="ready"` 且 embedding 非空。
- [x] 7.3 通过 `GET /items/search?q=<keyword>&mode=vector` 查询并断言返回该 chunk。
- [x] 7.4 覆盖 vector API 默认折叠同一 dedup group 的重复 version。
- [x] 7.5 运行 `uv run pytest tests/integration/test_vector_search_api_pipeline.py -q` 并确认通过。

## 8. 全量验证

- [x] 8.1 运行 `uv run pytest tests/search/test_vector_search.py tests/api/test_search.py tests/cli/test_search_cli_http_only.py tests/integration/test_vector_search_api_pipeline.py -q` 并确认通过。
- [x] 8.2 运行 `uv run pytest -q` 并确认全量测试通过。
- [x] 8.3 运行 `openspec validate expose-vector-search-api-cli --type change --strict` 并确认通过。
