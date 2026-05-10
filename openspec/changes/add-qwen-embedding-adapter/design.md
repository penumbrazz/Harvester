## Context

Harvester 的 embedding worker 和 vector search API 已经打通，但当前都硬编码使用 `StubModelAdapter`。这个 adapter 适合测试执行闭环，却没有真实语义质量。设计文档里已经把本地 Qwen embedding 服务列为基础设施之一，后续 LightRAG batch index 也依赖稳定的 embedding 模型、维度和模型名。

这个 change 把 embedding adapter 从“测试替身”升级为“可配置运行时边界”：生产环境使用本地 Qwen 服务，测试和离线开发继续使用 deterministic stub。Harvester 仍然只对 `item_version -> chunk` 做 embedding，raw HTML/API payload 不进入 embedding。

## Goals / Non-Goals

**Goals:**

- 新增 Qwen embedding adapter，通过本地 HTTP 服务生成 1536 维 embedding。
- 新增 adapter 配置和工厂，worker 与 vector query 共用同一配置路径。
- 保留 stub adapter 作为默认测试 adapter。
- 对模型服务超时、HTTP 错误、响应格式错误和维度不匹配给出可诊断错误。
- 在 chunk 写回时记录真实 `embedding_model`。
- 确保 vector search 的 query embedding 与 chunk embedding 使用兼容 adapter 和维度。

**Non-Goals:**

- 不引入 Qdrant 或新的向量数据库。
- 不改变 `chunks.embedding` 的 1536 维 pgvector schema。
- 不实现 LightRAG、rerank、hybrid ranking 或摘要。
- 不做 batch embedding 优化；第一版仍保持 `embed(text) -> list[float]`。
- 不对 raw payload 做 embedding。

## Decisions

1. **使用 OpenAI-compatible embeddings HTTP 协议作为第一版 Qwen adapter 接口。**

   请求形态为 `POST {base_url}/v1/embeddings`，body 包含 `model` 和 `input`。很多本地推理服务都能暴露 OpenAI-compatible API；这比直接绑定某一个运行时更可迁移。

   替代方案是直接支持 Ollama/vLLM/llama.cpp 各自协议。那会让第一版 adapter 变宽，并推迟真正验证语义搜索。

2. **新增 `EmbeddingSettings` 和 `create_embedding_adapter()` 工厂。**

   配置建议：
   - `HARVESTER_EMBEDDING_ADAPTER=stub|qwen`
   - `HARVESTER_EMBEDDING_MODEL`
   - `HARVESTER_EMBEDDING_DIMENSION=1536`
   - `HARVESTER_QWEN_EMBEDDING_BASE_URL`
   - `HARVESTER_QWEN_EMBEDDING_TIMEOUT_SECONDS`

   worker CLI、worker daemon 和 vector search API 都通过工厂创建 adapter，避免出现 worker 用 Qwen、query 还用 stub 的不一致。

3. **stub 继续作为默认 adapter。**

   如果没有配置 `HARVESTER_EMBEDDING_ADAPTER`，默认使用 stub。这样现有测试、离线开发和 CI 不依赖本地模型服务。生产部署通过 `.env` 显式切到 `qwen`。

   替代方案是默认要求 Qwen。这样更接近生产，但会让开发和 CI 变脆。

4. **维度校验保留在 handler 和 adapter 边界双层。**

   Qwen adapter 对返回向量做第一层维度和数值校验；`process_embed_chunks_job` 保留现有 1536 维校验，防止未来 adapter 绕过工厂或配置错误。

5. **错误分为配置错误和运行时错误，但都交给现有 retry 机制处理。**

   缺少 base URL、响应格式错误、HTTP 5xx、timeout 等都应产生清晰错误消息。worker 仍复用现有 `fail_job` 和 dead-letter 行为；API vector query 遇到 adapter 错误时返回请求可诊断的 503/500，不返回空结果伪装成功。

6. **运行时依赖使用 `httpx`。**

   代码库 CLI 和测试已经使用 `httpx`，Qwen adapter 也用它处理 timeout 和错误。需要把 `httpx` 从 dev-only 依赖提升为运行时依赖，避免生产镜像缺包。

## Risks / Trade-offs

- **[Risk] 本地 Qwen 服务协议不完全 OpenAI-compatible。** → Mitigation: adapter 单独封装请求/响应解析；如果实际服务不同，只替换 adapter，不影响 worker/search。
- **[Risk] query adapter 和 chunk adapter 配置不一致导致搜索质量差。** → Mitigation: worker 和 API 使用同一个 settings/factory，并记录 `embedding_model`。
- **[Risk] 模型服务慢导致 API vector search 变慢。** → Mitigation: 设置明确 timeout；后续可增加 query embedding cache，本 change 不先引入缓存。
- **[Risk] 维度配置和数据库 pgvector 维度不一致。** → Mitigation: settings 默认 1536，adapter 和 handler 都 MUST 校验 1536 维。
- **[Risk] 测试误触真实模型服务。** → Mitigation: 默认 adapter 为 stub；Qwen adapter 测试使用 mocked HTTP transport，不依赖外部服务。

## Migration Plan

1. 新增 adapter 工厂和 Qwen adapter，默认仍为 stub。
2. 更新 worker 和 vector search API 使用工厂，不改变现有默认行为。
3. 更新 `.env.example` 和 README，说明如何切换到本地 Qwen 服务。
4. 在本地模型服务可用后，设置 `HARVESTER_EMBEDDING_ADAPTER=qwen` 并运行 live smoke。
5. 回滚时删除或注释 Qwen 环境变量即可回到 stub，不需要数据库迁移。

## Open Questions

- 本地 Qwen embedding 服务最终暴露协议是否完全 OpenAI-compatible；第一版先按 OpenAI-compatible 设计。
- 生产模型名和实际维度需要实机确认；本 change 固定数据库维度为 1536。
- 是否需要 query embedding cache。第一版先不做，等真实延迟数据出来后再决定。
