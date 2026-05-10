## ADDED Requirements

### Requirement: 关键词搜索 API
系统 SHALL 提供 `GET /items/search` API，用已有关键词搜索能力查询资料库中的 latest item version。

#### Scenario: 成功返回搜索结果
- **WHEN** 客户端携带有效 API token 请求 `GET /items/search?q=Python`
- **THEN** 系统 MUST 返回 HTTP 200，并返回匹配 `q` 的搜索结果列表

#### Scenario: 缺少查询参数
- **WHEN** 客户端请求 `GET /items/search` 且未提供 `q`
- **THEN** 系统 MUST 返回请求参数错误，且不能执行数据库搜索

#### Scenario: 空白查询
- **WHEN** 客户端请求 `GET /items/search?q=   `
- **THEN** 系统 MUST 返回 HTTP 200 和空结果列表

### Requirement: 搜索 API 鉴权
系统 SHALL 要求搜索 API 使用 API token 认证。

#### Scenario: 未认证请求被拒绝
- **WHEN** 客户端未携带有效 `Authorization: Bearer <token>` 请求 `GET /items/search?q=Python`
- **THEN** 系统 MUST 返回 HTTP 401

#### Scenario: 错误 token 被拒绝
- **WHEN** 客户端携带错误 API token 请求 `GET /items/search?q=Python`
- **THEN** 系统 MUST 返回 HTTP 401

### Requirement: 搜索过滤和分页
系统 SHALL 支持按 source、topic、limit 和 offset 约束搜索结果。

#### Scenario: 按 source 过滤
- **WHEN** 客户端请求 `GET /items/search?q=Python&source_id=<source-id>`
- **THEN** 系统 MUST 只返回该 source 下匹配查询的结果

#### Scenario: 按 topic 过滤
- **WHEN** 客户端请求 `GET /items/search?q=Python&topic_watch_id=<topic-id>`
- **THEN** 系统 MUST 只返回该 topic watch 下匹配查询的结果

#### Scenario: 限制结果数量
- **WHEN** 客户端请求 `GET /items/search?q=Python&limit=5`
- **THEN** 系统 MUST 返回不超过 5 条结果

#### Scenario: 使用分页偏移
- **WHEN** 客户端请求 `GET /items/search?q=Python&offset=5`
- **THEN** 系统 MUST 将 offset 传递给搜索层并返回对应页面结果

### Requirement: 搜索结果契约
系统 SHALL 为每条搜索结果返回可追溯的结构化字段。

#### Scenario: 返回 item 和 version 标识
- **WHEN** 搜索结果匹配某个 content item
- **THEN** 结果项 MUST 包含 `item_id`、`version_id`、`source_id`、`title`、`canonical_url` 和 `created_at`

#### Scenario: 默认折叠重复结果
- **WHEN** 多个匹配版本属于同一个 dedup group
- **THEN** 搜索结果 MUST 默认只返回 canonical version 对应的结果

### Requirement: 搜索 CLI
系统 SHALL 提供 `harvester search "<query>"` 命令，通过 HTTP API 执行搜索。

#### Scenario: CLI 调用搜索 API
- **WHEN** 用户运行 `harvester search "Python"`
- **THEN** CLI MUST 发送 HTTP GET 请求到 `/items/search`，并将 `q=Python` 作为查询参数

#### Scenario: CLI 透传过滤参数
- **WHEN** 用户运行 `harvester search "Python" --source-id <source-id> --limit 5`
- **THEN** CLI MUST 将 `source_id` 和 `limit` 作为查询参数传给搜索 API

#### Scenario: CLI 不直接访问数据库
- **WHEN** 用户运行 `harvester search "Python"`
- **THEN** CLI MUST NOT 创建数据库 session 或直接调用 search repository

#### Scenario: CLI 输出可读结果
- **WHEN** 搜索 API 返回匹配结果
- **THEN** CLI MUST 输出每条结果的标题、item id、version id 和 source id

### Requirement: Raw-to-search 公开入口验证
系统 SHALL 通过集成测试验证抽取入库后的 content item 能通过搜索 API 被查询到。

#### Scenario: 抽取结果可通过 API 搜索
- **WHEN** fixture 或 fake adapter 产生的 item 经过 pipeline 写入 `content_item` 和 `item_version`
- **THEN** 使用 `GET /items/search?q=<keyword>` MUST 能返回该 item 的搜索结果
