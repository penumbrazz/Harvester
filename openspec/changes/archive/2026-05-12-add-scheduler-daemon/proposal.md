## Why

Harvester 已经有 watch schedule 表、API、one-shot scheduler 和 crawl job handler，但调度仍需要人工或外部 cron 反复触发，默认启动和 Compose 部署都不会自动产生 crawl job。为了让项目成为真正的 home lab 信息采集控制平面，需要把现有 one-shot 能力补成可长期运行、可停止、可观测的调度运行时。

## What Changes

- 增加 scheduler daemon 执行模式，按可配置 poll interval 周期调用现有 `run_scheduler_once`，只负责创建到期 crawl job，不直接执行网络抓取。
- 增加 crawl worker daemon 执行模式，让 `crawl` job 可以像 embedding job 一样长期消费，而不是只能手动 one-shot 处理。
- 增加进程级可观测性：daemon 启动参数、循环统计、错误日志和健康检查必须能区分 scheduler、crawl worker 与 embedding worker。
- 更新本地启动与部署基座，让开发者和 home lab 部署可以选择启动 scheduler 与 crawl worker，并保留当前 API 端口 `8001`、前端端口 `5173`、omlx 外部端口 `8000` 约定。
- 更新 smoke/集成测试，验证 schedule 到期后无需人工执行 one-shot 命令，也能被 daemon 自动入队并由 crawl worker 处理。
- 不新增复杂 cron 表达式、分布式 leader election、外部队列、登录态 recipe、LightRAG 或 MCP。

## Capabilities

### New Capabilities

- `scheduler-daemon`: 覆盖 watch scheduler 长期运行模式、crawl worker 长期运行模式、本地/Compose 启动集成、进程健康检查和自动调度闭环。

### Modified Capabilities

- `embedding-worker-daemon`: 保持默认 embedding worker 语义不变，同时明确 worker CLI/Compose 扩展后不得让 embedding worker 误消费 `crawl` job。

## Impact

- 影响 `harvester/jobs/scheduler.py`：需要复用或提取 one-shot 调度逻辑，并提供 loop/daemon 层。
- 影响 `harvester/workers/daemon.py` 和 `harvester/cli/main.py`：需要支持 crawl worker loop、scheduler daemon 命令和清晰的 job type 分发。
- 影响 `start.sh`、`docker-compose.yml`、`.env.example`、部署 smoke 脚本和 README：需要说明并验证 scheduler/crawl worker 的启动方式。
- 影响测试：新增 scheduler daemon、crawl worker daemon、CLI、Compose、smoke 和端到端自动调度测试。
- 不改变 raw/content 分层：scheduler 只创建 `crawl` job；embedding 仍然只能从 `item_version -> chunk` 开始，不能对 raw HTML/API payload 做 embedding。
