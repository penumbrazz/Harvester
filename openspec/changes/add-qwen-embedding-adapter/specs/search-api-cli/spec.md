## MODIFIED Requirements

### Requirement: Vector 查询 embedding
系统 SHALL 使用与 chunk embedding 兼容的配置化 adapter 为查询文本生成 embedding。

#### Scenario: 使用配置化 query embedding
- **WHEN** 客户端请求 vector 搜索
- **THEN** 系统 MUST 使用 embedding settings 创建 query embedding adapter，并生成 1536 维 query embedding

#### Scenario: Query embedding 维度正确
- **WHEN** query embedding 被传给 vector search
- **THEN** embedding 向量 MUST 为 1536 维

#### Scenario: Query adapter 与 worker adapter 兼容
- **WHEN** worker 使用 Qwen adapter 写入 chunk embedding
- **THEN** vector 搜索 API MUST 使用同一 embedding settings 生成 query embedding，避免固定使用 deterministic stub adapter

#### Scenario: Query embedding 失败返回错误
- **WHEN** vector 搜索 API 生成 query embedding 失败
- **THEN** 系统 MUST 返回可诊断的 HTTP 错误，且不能返回空结果伪装成功

### Requirement: Raw-to-vector 公开入口验证
系统 SHALL 通过集成测试验证 worker 生成 embedding 后可通过 vector 搜索 API 查询。

#### Scenario: Worker embedding 可通过 vector API 搜索
- **WHEN** chunk 经 embedding worker 写入 embedding 并标记为 ready
- **THEN** 使用 `GET /items/search?q=<keyword>&mode=vector` MUST 能返回该 chunk 的搜索结果

#### Scenario: 配置化 adapter 闭环可查询
- **WHEN** worker 和 vector search API 使用同一个配置化 embedding adapter
- **THEN** 系统 MUST 验证写入的 chunk embedding 可以被同一 adapter 生成的 query embedding 查询到
