## ADDED Requirements

### Requirement: Vector 搜索 API 模式
系统 SHALL 在 `GET /items/search` 中提供 vector 搜索模式。

#### Scenario: Vector 模式成功返回结果
- **WHEN** 客户端携带有效 API token 请求 `GET /items/search?q=Python&mode=vector`
- **THEN** 系统 MUST 使用查询文本生成 query embedding，并返回向量近邻搜索结果

#### Scenario: 默认保持关键词模式
- **WHEN** 客户端请求 `GET /items/search?q=Python` 且未提供 `mode`
- **THEN** 系统 MUST 保持现有关键词搜索行为

#### Scenario: 不支持的搜索模式被拒绝
- **WHEN** 客户端请求 `GET /items/search?q=Python&mode=unknown`
- **THEN** 系统 MUST 返回请求参数错误，且不能执行数据库搜索

#### Scenario: 空白 vector 查询返回空结果
- **WHEN** 客户端请求 `GET /items/search?q=   &mode=vector`
- **THEN** 系统 MUST 返回 HTTP 200 和空结果列表

### Requirement: Vector 查询 embedding
系统 SHALL 使用与第一版 embedding worker 兼容的 adapter 为查询文本生成 embedding。

#### Scenario: 使用 deterministic query embedding
- **WHEN** 客户端请求 vector 搜索
- **THEN** 系统 MUST 使用现有 deterministic embedding adapter 生成 1536 维 query embedding

#### Scenario: Query embedding 维度正确
- **WHEN** query embedding 被传给 vector search
- **THEN** embedding 向量 MUST 为 1536 维

### Requirement: Vector 搜索过滤
系统 SHALL 支持 vector 搜索按 source、topic 和 limit 约束结果。

#### Scenario: Vector 按 source 过滤
- **WHEN** 客户端请求 `GET /items/search?q=Python&mode=vector&source_id=<source-id>`
- **THEN** 系统 MUST 只返回该 source 下 ready chunk 的 vector 搜索结果

#### Scenario: Vector 按 topic 过滤
- **WHEN** 客户端请求 `GET /items/search?q=Python&mode=vector&topic_watch_id=<topic-id>`
- **THEN** 系统 MUST 只返回该 topic watch 下 ready chunk 的 vector 搜索结果

#### Scenario: Vector 限制结果数量
- **WHEN** 客户端请求 `GET /items/search?q=Python&mode=vector&limit=5`
- **THEN** 系统 MUST 返回不超过 5 条 vector 搜索结果

#### Scenario: Vector 只搜索 ready chunk
- **WHEN** 数据库中同时存在 pending chunk 和 ready chunk
- **THEN** vector 搜索 MUST 只返回 `embedding_status="ready"` 且 embedding 非空的 chunk

### Requirement: Vector 搜索结果契约
系统 SHALL 为 vector 搜索返回 chunk 级可追溯字段。

#### Scenario: 返回 chunk 级字段
- **WHEN** vector 搜索匹配某个 chunk
- **THEN** 结果项 MUST 包含 `chunk_id`、`item_version_id`、`content_item_id`、`title`、`text` 和 `distance`

#### Scenario: Vector 结果包含模式标识
- **WHEN** vector 搜索返回结果
- **THEN** 响应 MUST 标识该结果来自 `vector` 模式

#### Scenario: Vector 结果默认折叠重复内容
- **WHEN** 多个匹配 chunk 所属版本属于同一个 dedup group
- **THEN** vector 搜索结果 MUST 默认只返回 canonical version 对应的结果

### Requirement: Vector 搜索 CLI 模式
系统 SHALL 通过现有 `harvester search` 命令暴露 vector 搜索。

#### Scenario: CLI 调用 vector 搜索 API
- **WHEN** 用户运行 `harvester search "Python" --mode vector`
- **THEN** CLI MUST 发送 HTTP GET 请求到 `/items/search`，并将 `q=Python` 和 `mode=vector` 作为查询参数

#### Scenario: CLI 透传 vector 过滤参数
- **WHEN** 用户运行 `harvester search "Python" --mode vector --source-id <source-id> --limit 5`
- **THEN** CLI MUST 将 `mode`、`source_id` 和 `limit` 作为查询参数传给搜索 API

#### Scenario: CLI 输出 vector 结果
- **WHEN** vector 搜索 API 返回匹配结果
- **THEN** CLI MUST 输出每条结果的标题、chunk id、item version id 和 distance

#### Scenario: CLI 保持 HTTP-only
- **WHEN** 用户运行 `harvester search "Python" --mode vector`
- **THEN** CLI MUST NOT 创建数据库 session、直接调用 model adapter 或直接调用 vector search

### Requirement: Raw-to-vector 公开入口验证
系统 SHALL 通过集成测试验证 worker 生成 embedding 后可通过 vector 搜索 API 查询。

#### Scenario: Worker embedding 可通过 vector API 搜索
- **WHEN** chunk 经 embedding worker 写入 embedding 并标记为 ready
- **THEN** 使用 `GET /items/search?q=<keyword>&mode=vector` MUST 能返回该 chunk 的搜索结果
