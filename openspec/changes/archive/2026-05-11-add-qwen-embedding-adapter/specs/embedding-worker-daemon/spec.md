## MODIFIED Requirements

### Requirement: Embed chunks job handler
系统 SHALL 提供 `embed_chunks` job handler，用于通过配置化 embedding adapter 将 chunk text 转换为 embedding 并写回 `chunks` 表。

#### Scenario: 成功处理 chunk embedding
- **WHEN** worker 收到 payload 包含有效 `chunk_id` 的 `embed_chunks` job
- **THEN** 系统 MUST 读取对应 chunk 的 `text`，使用配置化 embedding adapter 生成 1536 维 embedding，并写入 `chunks.embedding`

#### Scenario: 写入 embedding 状态
- **WHEN** chunk embedding 成功生成并保存
- **THEN** 系统 MUST 将该 chunk 的 `embedding_status` 更新为 `ready`，并写入非空 `embedding_model`

#### Scenario: 已 ready 的 chunk 不重复 embedding
- **WHEN** worker 收到的 job 指向 `embedding_status="ready"` 的 chunk
- **THEN** 系统 MUST 不重新生成 embedding，并将 job 标记为 completed

#### Scenario: Stub adapter 仍可用于测试
- **WHEN** worker 使用 deterministic stub adapter 处理 `embed_chunks` job
- **THEN** 系统 MUST 保持现有离线测试行为，并生成 1536 维 deterministic embedding

### Requirement: Worker CLI
系统 SHALL 通过 CLI 暴露 worker 运行入口，并使用配置化 embedding adapter。

#### Scenario: CLI one-shot 入口
- **WHEN** 用户运行 `harvester worker once --limit 1`
- **THEN** CLI MUST 根据 embedding settings 创建 adapter，执行一次 embedding worker 处理，并输出处理统计

#### Scenario: CLI loop 入口
- **WHEN** 用户运行 `harvester worker run --poll-interval 5`
- **THEN** CLI MUST 根据 embedding settings 创建 adapter，启动 loop worker，并使用指定轮询间隔

#### Scenario: CLI 配置为 Qwen adapter
- **WHEN** 用户运行 worker CLI 且 `HARVESTER_EMBEDDING_ADAPTER=qwen`
- **THEN** CLI MUST 使用 Qwen embedding adapter 处理 chunk embedding
