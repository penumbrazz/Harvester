## Why

Harvester 已经有 `keyword_search` 和 pgvector-ready search 内核，但用户和 agent 还不能通过 API/CLI 直接查询资料库。现在已经打通公开抓取、抽取、去重和 chunk 创建，下一步应补齐第一版“抓取到搜索”的可操作入口。

## What Changes

- 新增只读搜索 API：`GET /items/search?q=...`，返回 latest item version 的可追溯结果。
- 搜索 API 支持 `source_id`、`topic_watch_id`、`limit`、`offset` 过滤和分页参数。
- 新增 CLI 命令 `harvester search "<query>"`，通过 HTTP API 查询，不直接访问数据库。
- 搜索结果默认复用现有 dedup collapse 行为，避免重复内容刷屏。
- 新增 API、CLI 和集成测试，证明抓取/抽取后的 item 可以通过公开入口被搜索到。
- 本 change 不实现 LightRAG、KG、实际 embedding worker 或向量查询入口。

## Capabilities

### New Capabilities

- `search-api-cli`: 资料库搜索 API 和 CLI 入口，包括关键词查询、过滤、分页、去重折叠和可追溯结果字段。

### Modified Capabilities

## Impact

- 新增 API router，例如 `harvester/api/routers/search.py`，并在 FastAPI app 注册。
- 扩展 CLI，例如在 `harvester/cli/main.py` 增加 `search` 命令。
- 复用现有 `harvester/search/keyword.py` 和 `harvester/search/dedup.py`。
- 新增或扩展 `tests/api/`、`tests/cli/`、`tests/integration/` 中的测试。
- 不新增外部依赖，不修改生产数据库 schema。
