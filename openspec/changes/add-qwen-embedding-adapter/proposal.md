## Why

Harvester 现在的 embedding 闭环使用 deterministic stub adapter，只能验证执行路径，不能提供真实语义检索质量。下一步需要接入本地 Qwen embedding 服务，让 `item_version -> chunk -> embedding -> vector search` 成为可用的语义搜索基础，并为后续 LightRAG batch index 固定模型和维度边界。

## What Changes

- 增加 Qwen embedding adapter，支持通过配置调用本地模型服务生成 embedding。
- 增加 embedding adapter 工厂，让 worker 和 vector query 使用同一类 adapter 配置。
- 保留 deterministic stub adapter 作为测试和离线开发默认能力。
- 为 adapter 增加超时、错误归类、维度校验和模型名记录。
- 让 embedding worker 可通过环境变量选择 `stub` 或 `qwen` adapter。
- 让 vector search API 使用与 chunk embedding 兼容的 query embedding adapter。
- 不引入 Qdrant，不改变 `chunks.embedding` 的 1536 维 pgvector 存储，不对 raw HTML/API payload 做 embedding。

## Capabilities

### New Capabilities

- `qwen-embedding-adapter`: Qwen embedding adapter 配置、HTTP 调用、错误处理、维度校验和模型标识。

### Modified Capabilities

- `embedding-worker-daemon`: embedding worker 从硬编码 stub 扩展为使用可配置 embedding adapter，同时保留现有 job claim、retry 和 ready/failed 状态行为。
- `search-api-cli`: vector 搜索的 query embedding 从固定 deterministic adapter 调整为使用与 chunk embedding 兼容的配置化 adapter。

## Impact

- 影响 `harvester/adapters/`：新增 Qwen adapter、adapter 配置和工厂。
- 影响 `harvester/workers/`：worker CLI/daemon 初始化 adapter 的方式从硬编码 stub 改为配置化创建。
- 影响 `harvester/api/routers/search.py`：vector query embedding 改为通过配置化 adapter 创建，必须与 chunk embedding 维度一致。
- 影响 `.env.example`、README 和 Docker/worker 配置：新增本地模型服务 URL、模型名、adapter 类型、超时和维度配置说明。
- 影响测试：新增 adapter 单元测试、配置测试、worker 使用 Qwen adapter 的 mock 测试、vector API query adapter 一致性测试。
