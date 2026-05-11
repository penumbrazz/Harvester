## Why

Harvester 已经能手动执行公开网页抓取、抽取、去重、embedding 和搜索，但还不能作为长期运行的 watch 系统自动产生新 crawl。下一步需要把 Source Watch 和 Topic Watch 接到 Postgres job 队列，让 CDC weekly、Sina 7x24 和临时 Topic Watch 可以持续运行，而不是依赖人工反复调用 `/crawl/run`。

## What Changes

- 增加 watch scheduler：扫描可运行的 watched/active source 与 active topic-source 关系，按调度策略创建 `crawl` job。
- 增加 `crawl` job handler：worker 消费 crawl job，复用现有 `execute_crawl`、fetch policy、archive、audit 和 retry/dead-letter 机制。
- 增加调度幂等：同一 source、recipe、topic 和调度窗口不能重复创建 crawl job。
- 增加 Topic Watch TTL 行为：过期 topic 不再产生新的 crawl job。
- 增加高频来源保护：调度时保留现有 frontier/rewind 思路，不让同一 source 的 crawl job 刷爆队列。
- 增加 CLI 入口，用于执行一次 scheduler、执行 crawl worker one-shot，并查看基础队列状态。
- 不实现新的 extractor、LightRAG、MCP、登录态 recipe 或浏览器 profile。

## Capabilities

### New Capabilities

- `watch-scheduler-crawl-worker`: Source/Topic Watch 调度、crawl job 创建、crawl job worker 执行、幂等与 TTL 行为。

### Modified Capabilities

无。

## Impact

- 影响 `harvester/jobs/`：新增 scheduler 和 crawl job handler，复用现有 job repository 与 crawl execution service。
- 影响 `harvester/workers/`：worker daemon 需要支持多个 job type 的 handler 分发。
- 影响 `harvester/cli/`：新增 scheduler/queue 相关命令，保持 CLI 状态变更通过 HTTP API 或明确的本地 worker/scheduler 运维入口。
- 影响数据库模型或迁移：可能需要为 source/recipe/topic 增加调度字段，或新增最小调度状态表；必须保留已有 raw/content 分层。
- 影响测试：新增 scheduler、crawl job worker、TTL、幂等、retry、CLI 和集成测试。
