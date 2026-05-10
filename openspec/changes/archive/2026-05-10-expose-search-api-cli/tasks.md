## 1. API 测试

- [x] 1.1 创建 `tests/api/test_search.py`，覆盖 `GET /items/search` 需要 API token、缺少 `q` 返回参数错误、空白 `q` 返回空结果。
- [x] 1.2 在 `tests/api/test_search.py` 中准备 source/content_item/item_version fixture，覆盖成功搜索、`source_id` 过滤、`topic_watch_id` 过滤、`limit` 和 `offset` 参数。
- [x] 1.3 在 API 测试中断言响应字段包含 `item_id`、`version_id`、`source_id`、`title`、`canonical_url`、`created_at`。

## 2. API 实现

- [x] 2.1 新增 `harvester/api/routers/search.py`，定义 `SearchItem`、`SearchResponse` 和 `GET /items/search` endpoint。
- [x] 2.2 在搜索 endpoint 中复用 `require_api_token`、`get_db_session` 和 `keyword_search`，实现 `q`、`source_id`、`topic_watch_id`、`limit`、`offset` 参数处理。
- [x] 2.3 在 `harvester/api/app.py` 注册 search router。
- [x] 2.4 运行 `uv run pytest tests/api/test_search.py -q` 并确认通过。

## 3. CLI 测试

- [x] 3.1 创建或扩展 CLI 测试，覆盖 `harvester search "Python"` 使用 `httpx.get` 调 `/items/search`，并传递 `q` 参数。
- [x] 3.2 覆盖 CLI `--source-id`、`--topic-watch-id`、`--limit`、`--offset` 参数透传。
- [x] 3.3 覆盖 CLI 输出标题、item id、version id 和 source id。
- [x] 3.4 覆盖 CLI 不直接导入数据库 session 或调用 search module。

## 4. CLI 实现

- [x] 4.1 在 `harvester/cli/main.py` 增加 `search` 命令，复用 `_get_base_url()` 和 `_api_headers()`。
- [x] 4.2 实现搜索请求、错误处理和空结果输出。
- [x] 4.3 运行 `uv run pytest tests/cli/test_cli_http_only.py tests/cli/test_crawl_cli_http_only.py -q` 或新增对应 CLI 测试文件并确认通过。

## 5. 集成验证

- [x] 5.1 新增或扩展集成测试，使用 fixture/fake adapter 将 item 写入 `content_item` 和 `item_version` 后，通过 `GET /items/search` 查询到结果。
- [x] 5.2 验证搜索结果默认复用 dedup collapse 行为，重复 group 只返回 canonical 结果。
- [x] 5.3 运行 `uv run pytest tests/integration/ tests/search/ -q` 并确认通过。

## 6. 全量验证

- [x] 6.1 运行 `uv run pytest -q` 并确认全量测试通过。
- [x] 6.2 运行 `openspec validate expose-search-api-cli --type change --strict` 并确认通过。
