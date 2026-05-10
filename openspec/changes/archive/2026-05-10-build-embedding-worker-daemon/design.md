## Context

Harvester 当前已经具备三块前置能力：

- `chunks` 表包含 `embedding`、`embedding_model`、`embedding_status` 字段，向量维度固定为 1536。
- pipeline 会创建 `embed_chunks` job。
- `claim_next_jobs`、`complete_job`、`fail_job` 已经提供 Postgres-backed job lease、retry 和 dead-letter 机制。

缺口是执行层：没有长期运行的 worker daemon 消费 `embed_chunks` job，Docker Compose 里的 worker 也只是启动 CLI 入口。这个 change 只补 embedding job 执行闭环，先用现有 deterministic `StubModelAdapter`，为后续替换为本地 Qwen embedding 服务保留 adapter 边界。

## Goals / Non-Goals

**Goals:**

- 实现单个 `embed_chunks` job 的处理逻辑。
- worker 从 job payload 读取 `chunk_id`，加载对应 chunk，调用 embedding adapter，并写回 chunk embedding。
- 成功处理后将 chunk 标记为 `embedding_status="ready"`，并写入 `embedding_model`。
- job 成功时调用 `complete_job`，失败时调用 `fail_job`。
- 支持 one-shot worker，便于测试、手动运行和 smoke。
- 支持 loop worker，供 Docker Compose 长时间运行。
- 更新 Docker Compose worker command，使 worker service 真正消费 job。

**Non-Goals:**

- 不实现真实 Qwen、本地模型 HTTP 服务或外部 embedding provider。
- 不实现 LightRAG、KG 或 batch index。
- 不新增向量搜索 API/CLI。
- 不修改数据库 schema 或向量维度。
- 不重新设计现有 job retry 语义。

## Decisions

1. **新建 worker 模块，不把 daemon 逻辑塞进 CLI。**
   - 选择：新增 `harvester/workers/embedding.py` 处理单 job，新增 `harvester/workers/daemon.py` 管理 claim/loop。
   - 原因：CLI 只做入口，worker 行为需要可被单元测试和集成测试直接调用。
   - 替代方案：全部写在 `harvester/cli/main.py`。实现更少，但会让 CLI 文件继续膨胀，也不利于复用。

2. **第一版只消费 `embed_chunks` lane。**
   - 选择：daemon 调用 `claim_next_jobs(..., lanes=["embed_chunks"])`。
   - 原因：当前要补的是 embedding 执行闭环；crawl/extract 等 job 类型已有同步 API/测试路径，不在本 change 混入多类型 dispatcher。
   - 替代方案：实现通用 job dispatcher。长期合理，但会扩大范围，需要定义 job handler registry。

3. **使用 `StubModelAdapter`，并记录固定模型名。**
   - 选择：默认 adapter 为 `StubModelAdapter`，`embedding_model` 写入稳定字符串，例如 `stub-embedding-1536`。
   - 原因：不依赖网络或本地模型进程，能让 MVP 在 CI、Docker smoke 和 home lab 初始部署中稳定运行。
   - 替代方案：直接接本地 Qwen embedding 服务。更接近最终目标，但会引入服务发现、超时、维度校验和失败模式。

4. **失败处理不提前阻断 retry。**
   - 选择：adapter 异常或可恢复错误时调用 `fail_job`，chunk 保持 `embedding_status="pending"`；只有确定无效 payload、缺失 chunk，或 job 已到最后一次尝试时，才把 chunk 标记为 `failed`。
   - 原因：如果第一次失败就把 chunk 标为 `failed`，后续 retry job 可能被处理逻辑跳过，导致 retry 形同虚设。
   - 替代方案：任何失败都立即标记 chunk failed。实现简单，但不符合 job retry 语义。

5. **worker one-shot 返回处理计数，loop 只负责重复执行。**
   - 选择：`run_once(limit=N)` 认领并处理一批 job，返回 completed/failed/claimed 统计；`run_loop` 轮询调用 `run_once`，空闲时 sleep。
   - 原因：one-shot 易测试，loop 行为只需验证空闲、sleep 和停止条件。
   - 替代方案：只提供无限 loop。测试复杂，也不适合 smoke。

6. **CLI 提供 `worker once` 和 `worker run`。**
   - 选择：`harvester worker once --limit N` 用于一次性处理，`harvester worker run --poll-interval S` 用于 daemon。
   - 原因：既满足本地调试，也能作为 Docker Compose command。
   - 替代方案：只提供 `python -m harvester.workers.daemon`。可行，但和项目已有 Typer CLI 入口不一致。

## Risks / Trade-offs

- **[Risk] Stub embedding 不具备语义质量。** → Mitigation: 明确它只用于执行闭环和测试；后续独立 change 替换 adapter。
- **[Risk] 现有 retry job 的 attempts 语义可能不足以跨 retry job 累积。** → Mitigation: 本 change 复用现有机制，不重写队列；worker 只保证调用 `fail_job` 并覆盖当前机制下的行为。
- **[Risk] 长时间 loop 可能吞掉异常。** → Mitigation: 单 job handler 捕获异常并失败 job；loop 只捕获外层异常用于记录和继续/停止，测试覆盖 adapter failure。
- **[Risk] compose healthcheck 只能证明进程存在，不能证明处理成功。** → Mitigation: deploy 测试只验证 worker command/healthcheck；真实处理能力由 worker/integration 测试覆盖。

## Migration Plan

- 无数据库迁移。
- 部署时更新代码和 `docker-compose.yml`，重启 worker service。
- rollback 时把 worker command 改回旧命令或停止 worker；未处理的 `embed_chunks` job 会留在 pending/running，过期 lease 可被后续 worker 回收。

## Open Questions

- 后续真实 embedding adapter 的服务协议、超时、批量大小和模型名称需要单独设计。
- 是否需要通用 job dispatcher registry，应在 crawl/extract/retention 等异步 job 都进入 daemon 后再统一设计。
