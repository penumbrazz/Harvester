## ADDED Requirements

### Requirement: Qwen embedding adapter 配置
系统 SHALL 提供可配置的 Qwen embedding adapter，用于调用本地模型服务生成 embedding。

#### Scenario: 使用 Qwen adapter 配置
- **WHEN** `HARVESTER_EMBEDDING_ADAPTER=qwen`
- **THEN** 系统 MUST 使用 Qwen embedding adapter，而不能使用 deterministic stub adapter

#### Scenario: 默认使用 stub adapter
- **WHEN** 未设置 `HARVESTER_EMBEDDING_ADAPTER`
- **THEN** 系统 MUST 默认使用 deterministic stub adapter，保证离线测试不依赖模型服务

#### Scenario: Qwen adapter 缺少 base URL
- **WHEN** adapter 类型为 `qwen` 且缺少本地模型服务 base URL
- **THEN** 系统 MUST 报告配置错误，且不能静默回退到 stub adapter

### Requirement: OpenAI-compatible embedding 请求
系统 SHALL 通过 OpenAI-compatible embeddings HTTP 协议调用本地 Qwen 服务。

#### Scenario: 发送 embeddings 请求
- **WHEN** Qwen adapter 为文本生成 embedding
- **THEN** 系统 MUST 向配置的 `/v1/embeddings` endpoint 发送包含 `model` 和 `input` 的请求

#### Scenario: 解析 embeddings 响应
- **WHEN** 本地模型服务返回 OpenAI-compatible embeddings 响应
- **THEN** 系统 MUST 从第一条 data item 中读取 embedding 向量

#### Scenario: 记录模型名
- **WHEN** Qwen adapter 成功生成 embedding
- **THEN** 调用方 MUST 能获得配置的 embedding model 名称用于写入 `chunks.embedding_model`

### Requirement: Embedding 维度与数值校验
系统 SHALL 校验 Qwen adapter 返回的 embedding 可以写入现有 pgvector schema。

#### Scenario: 返回 1536 维向量
- **WHEN** Qwen adapter 返回 embedding
- **THEN** embedding 向量 MUST 正好包含 1536 个有限 float 值

#### Scenario: 维度不匹配被拒绝
- **WHEN** 本地模型服务返回非 1536 维 embedding
- **THEN** 系统 MUST 报告维度错误，且不能把该 embedding 写入数据库

#### Scenario: 非数值向量被拒绝
- **WHEN** 本地模型服务返回包含非数值或非有限值的 embedding
- **THEN** 系统 MUST 报告响应格式错误，且不能把该 embedding 写入数据库

### Requirement: Qwen adapter 错误处理
系统 SHALL 对本地模型服务错误提供可诊断失败信息。

#### Scenario: 模型服务 timeout
- **WHEN** Qwen adapter 调用本地模型服务超时
- **THEN** 系统 MUST 抛出可诊断的 adapter 错误，供 worker retry 或 API 返回错误

#### Scenario: 模型服务 HTTP 错误
- **WHEN** 本地模型服务返回非 2xx HTTP 响应
- **THEN** 系统 MUST 抛出包含 HTTP 状态的 adapter 错误

#### Scenario: 响应 JSON 格式错误
- **WHEN** 本地模型服务返回缺少 embedding 字段的响应
- **THEN** 系统 MUST 抛出响应格式错误

### Requirement: Qwen adapter 测试隔离
系统 SHALL 在测试中 mock 本地模型服务，避免单元测试依赖真实网络。

#### Scenario: 单元测试不访问真实 Qwen 服务
- **WHEN** 运行 Qwen adapter 单元测试
- **THEN** 测试 MUST 使用 mocked HTTP transport 或等价机制，且不能要求真实模型服务运行

#### Scenario: 可选 live smoke
- **WHEN** 显式启用 live Qwen smoke 环境变量
- **THEN** 系统 MUST 调用真实本地模型服务验证配置
