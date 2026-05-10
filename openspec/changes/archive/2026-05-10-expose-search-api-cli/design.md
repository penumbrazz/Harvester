## Context

Harvester 的搜索内核已经存在：`keyword_search` 查询 latest item version，并通过 `collapse_dedup_groups` 默认折叠重复结果；`vector_search` 和 chunk embedding 字段也已经为后续向量检索准备好。当前缺口在入口层：FastAPI app 没有注册搜索 router，CLI 也没有 `search` 命令，用户和 agent 只能通过内部 Python 函数验证搜索。

这个 change 是第一版“抓取 → raw evidence → content item → item version/chunk → search”闭环的入口补齐，不改变 schema，也不引入 LightRAG。

## Goals / Non-Goals

**Goals:**

- 提供 `GET /items/search` 只读 API，基于已有 `keyword_search` 返回搜索结果。
- API 结果包含可追溯字段：`item_id`、`version_id`、`source_id`、`title`、`canonical_url`、`created_at`。
- 支持 `source_id`、`topic_watch_id`、`limit`、`offset` 参数。
- 搜索入口要求 API token，避免本地资料库通过未认证 HTTP 暴露。
- 提供 `harvester search "<query>"` CLI 命令，CLI 只调用 HTTP API，不直接创建数据库 session。
- 通过 API、CLI 和集成测试证明抽取入库后的 item 可以通过公开入口搜索到。

**Non-Goals:**

- 不实现 LightRAG batch index、KG 或 MCP adapter。
- 不实现真实 embedding worker。
- 不开放向量搜索 API/CLI。
- 不修改数据库 schema 或 search index migration。
- 不重新设计 `keyword_search` 排名算法。

## Decisions

1. **搜索 API 使用 `/items/search`，不放在 `/search`。**
   - 选择：新增 `harvester/api/routers/search.py`，router prefix 为 `/items`，端点为 `GET /items/search`。
   - 原因：搜索返回的是资料库 content item / latest version，而不是系统级全文搜索服务；路径更贴近被查询资源。
   - 替代方案：`GET /search`。更短，但后续 topic、audit、raw evidence 搜索扩展时语义容易变宽。

2. **第一版入口只暴露 keyword search。**
   - 选择：API 调用 `keyword_search`，不暴露 `vector_search`。
   - 原因：当前已有 keyword search 的稳定测试；向量搜索依赖 chunk embedding readiness 和 embedding worker，入口过早开放会产生“能调用但没有结果”的体验。
   - 替代方案：同时开放 `mode=keyword|vector`。这会把 embedding 模型、查询向量生成和错误处理拉进本 change，超出范围。

3. **搜索 API 继续要求 API token。**
   - 选择：复用 `require_api_token`。
   - 原因：搜索结果可能包含个人 home lab 资料库内容，即使是只读入口也不能匿名暴露。
   - 替代方案：把搜索作为 public read endpoint。实现简单，但不符合当前 README 中 API token 覆盖 SearchAPI 的边界。

4. **CLI 使用 `httpx.get` 调 API，不导入数据库或 search module。**
   - 选择：`harvester search "<query>"` 构造 query params，复用 `_get_base_url()` 和 `_api_headers()`。
   - 原因：项目约束要求 CLI 状态变更必须走 HTTP API；搜索虽然只读，也应保持 agent 操作入口一致，避免 CLI 绕过 API auth 和响应契约。
   - 替代方案：CLI 直接调用 `keyword_search`。会更快，但破坏 API-first 操作模型，也让本地环境必须有数据库连接。

5. **API response 使用显式 Pydantic model。**
   - 选择：定义 `SearchItem` 和 `SearchResponse`，从 `keyword_search` 的 dict 结果转换为字符串 UUID 和 datetime。
   - 原因：保持响应稳定，方便 CLI 和 agent 依赖字段。
   - 替代方案：直接返回 `list[dict]`。实现更少，但契约不清晰，后续字段变更风险更高。

## Risks / Trade-offs

- **[Risk] 当前 keyword search 只查 title，用户可能以为会搜索正文。** → Mitigation: 端点命名保持泛化但 spec 明确第一版是关键词标题搜索；后续可在独立 change 中扩展到 chunk text。
- **[Risk] dedup collapse 后分页可能少于 limit。** → Mitigation: 复用现有 `keyword_search` 的 over-fetch 行为，本 change 不重新设计分页一致性。
- **[Risk] API token 让本地手动搜索多一步配置。** → Mitigation: CLI 已复用 `HARVESTER_API_TOKEN`，和现有命令保持一致。
- **[Risk] 搜索结果没有 raw payload。** → Mitigation: 这是架构要求；结果返回 item/version/source 标识，raw evidence 通过后续 failure/audit/evidence inspection 能力追溯。

## Migration Plan

- 无 schema migration。
- 部署时只需发布 API/CLI 代码并重启 server。
- rollback 可移除 router 注册和 CLI 命令；不会影响已有数据。

## Open Questions

- 后续是否把 chunk text 纳入 keyword search，需要单独设计 ranking、snippet 和性能边界。
- 向量搜索入口应等待真实 embedding worker 和查询 embedding adapter 稳定后再提出。
