## Context

当前搜索入口已经完成关键词查询：`GET /items/search?q=...` 和 `harvester search "<query>"` 都调用 `keyword_search`，返回 content item / latest version 级结果。embedding worker 已经补齐 `embed_chunks` job 执行闭环，chunk 可以进入 `embedding_status="ready"` 并拥有 1536 维 embedding。`vector_search` 内核也已存在，但只在 Python 内部可用。

这个 change 的目标是把已有向量检索能力接到公开 API/CLI。它仍属于 `search-api-cli` 能力扩展，不改变 raw evidence 和 content item 的核心边界。

## Goals / Non-Goals

**Goals:**

- 在 `GET /items/search` 上增加 `mode=vector`，默认 `mode=keyword` 保持兼容。
- vector 模式将查询文本转换为 query embedding，并调用 `vector_search`。
- vector 模式只查询 `embedding_status="ready"` 且 embedding 非空的 chunk。
- vector 结果返回 chunk 级字段：`chunk_id`、`item_version_id`、`content_item_id`、`title`、`text` 或 snippet、`distance`。
- vector 模式支持 `limit`、`source_id`、`topic_watch_id`。
- CLI 增加 `--mode vector`，继续只通过 HTTP API 搜索，不直接访问数据库。
- 集成测试覆盖：chunk 由 worker 生成 embedding 后，可以通过 API vector mode 搜到。

**Non-Goals:**

- 不实现 LightRAG、KG 或 MCP adapter。
- 不实现真实 Qwen embedding 服务。
- 不引入 hybrid ranking 或 keyword/vector 结果融合。
- 不修改数据库 schema 或向量维度。
- 不改变默认 keyword 搜索响应行为。

## Decisions

1. **复用 `/items/search`，用 `mode` 区分 keyword/vector。**
   - 选择：新增 query 参数 `mode=keyword|vector`，默认 `keyword`。
   - 原因：用户和 agent 已经有统一搜索入口；vector 是搜索模式，不需要新资源路径。
   - 替代方案：新增 `/items/vector-search`。语义清楚，但会产生两个搜索入口和重复鉴权/过滤逻辑。

2. **query embedding 第一版使用 `StubModelAdapter`。**
   - 选择：API 内部用现有 `StubModelAdapter` 对 `q` 生成 1536 维 query embedding。
   - 原因：worker 第一版也使用 deterministic stub embedding，查询端必须使用同一 adapter 才能在测试和 home lab 初始部署中稳定闭环。
   - 替代方案：引入真实模型服务配置。更接近最终目标，但会引入网络、超时、模型维度和部署依赖，适合后续独立 change。

3. **扩展 `vector_search` 支持 source/topic 过滤。**
   - 选择：在 `vector_search` 中增加 `source_id`、`topic_watch_id` 可选参数。
   - 原因：API 已经承诺 search 过滤语义，vector 模式应与 keyword 模式一致。
   - 替代方案：API 层过滤结果。会先取错范围再过滤，limit 和 dedup 语义不可靠。

4. **响应模型允许 keyword 和 vector 两类结果。**
   - 选择：`SearchResponse.items` 使用统一字段 superset，keyword 结果填 `item_id/version_id/source_id/title/canonical_url/created_at`，vector 结果额外填 `chunk_id/text/distance`，并可设置 `mode`。
   - 原因：保持一个 endpoint 和 CLI 输出路径，同时让 vector 的 chunk 级信息可追溯。
   - 替代方案：完全不同 response model。类型更严格，但会让客户端按 endpoint/mode 写两套解析。

5. **CLI 只透传 mode 和过滤参数。**
   - 选择：`harvester search "..." --mode vector` 发送 `mode=vector` 到 API，输出 chunk/title/distance。
   - 原因：CLI 继续保持 HTTP-only，不承担 embedding 生成或数据库查询。
   - 替代方案：CLI 直接调用 `StubModelAdapter` 和 `vector_search`。违反现有 CLI 操作边界。

## Risks / Trade-offs

- **[Risk] Stub embedding 不具备真实语义质量。** → Mitigation: 明确本 change 是暴露执行闭环，后续真实 model adapter 单独替换。
- **[Risk] keyword 和 vector 返回字段不同，客户端解析复杂。** → Mitigation: 响应包含 `mode`，并为 vector 字段使用 nullable 字段，CLI 按 mode 格式化。
- **[Risk] vector 搜索没有 offset。** → Mitigation: 第一版只支持 `limit`；offset 对近邻检索意义弱，后续如需要再设计。
- **[Risk] 查询时没有 ready embedding 会返回空结果。** → Mitigation: 这是正确行为；集成测试覆盖 worker 先生成 embedding 再搜索。

## Migration Plan

- 无数据库迁移。
- 部署时发布 API/CLI 代码即可。
- 默认 `mode=keyword`，现有 `/items/search?q=...` 调用不需要修改。
- rollback 时移除 `mode=vector` 分支和 CLI 参数，不影响 keyword 搜索。

## Open Questions

- 真实 embedding adapter 的配置、模型名和维度校验需要后续 change 明确。
- 后续是否需要 hybrid search，应在 keyword/vector 两条入口稳定后再设计排序和解释字段。
