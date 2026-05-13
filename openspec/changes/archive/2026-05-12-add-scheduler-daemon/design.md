## Context

当前 Harvester 已经具备调度所需的核心积木：`watch_schedules` 持久化表、schedule API/CLI、`run_scheduler_once`、`crawl` job handler、`worker once --job-type crawl` 和队列状态查看。缺口在运行时编排：`scheduler run` 是 one-shot，crawl worker 也只能 one-shot，`start.sh` 默认只启动后端和前端，`docker-compose.yml` 只有 API server 与 embedding worker。因此系统配置了 schedule 后，并不会自动持续产生和消费 crawl job。

本 change 不重做 schedule schema 或抓取 pipeline，而是把已有 one-shot 能力包装成长期运行的进程，并让本地开发与 home lab Compose 部署都能显式启动这些进程。

## Goals / Non-Goals

**Goals:**

- 提供 scheduler daemon：周期性扫描到期 schedule 并创建 `crawl` job。
- 提供 crawl worker daemon：长期消费 `crawl` job，复用现有 `process_crawl_job`。
- 保持默认 embedding worker 行为不变，避免新增 daemon 后误消费其他 job type。
- 为 CLI、`start.sh`、Docker Compose、`.env.example` 和 README 提供一致的启动入口与配置说明。
- 用测试覆盖 loop 行为、job type 隔离、进程配置、健康检查和自动调度端到端闭环。

**Non-Goals:**

- 不新增 cron 表达式、日历规则、jitter 或复杂调度 DSL；仍使用当前 `interval_seconds`。
- 不引入 Celery、Redis、APScheduler、systemd SDK 或 Kubernetes controller。
- 不实现分布式 leader election。第一版允许多 scheduler 进程并发运行，依赖现有 schedule window idempotency 防重复 job。
- 不改变 `raw_object`、`content_item`、`item_version`、`chunk` 分层，也不对 raw HTML/API payload 做 embedding。
- 不新增登录态 recipe、浏览器 profile、LightRAG、MCP 或 source discovery。

## Decisions

1. **在 one-shot 函数外增加 loop wrapper，而不是把循环逻辑塞进 `run_scheduler_once`。**

   `run_scheduler_once(session, now, limit)` 继续保持短事务、可测试和可手动调用。新增 `run_scheduler_loop(session_factory, poll_interval, limit, should_stop)` 每轮创建 session、调用 one-shot、记录统计、按配置 sleep。这样单轮语义不会被 daemon 复杂性污染，现有测试也不需要重写。

   备选方案是让 `run_scheduler_once` 自己支持 `forever=True`。这会让函数承担两种生命周期，测试和错误处理边界都更差。

2. **复用 worker daemon 的 job type 分发，但默认仍只处理 `embed_chunks`。**

   `harvester worker run` 不带 `--job-type` 时继续启动 embedding worker；新增 `harvester worker run --job-type crawl` 启动 crawl worker loop。`worker once --job-type crawl` 已有语义需要保持，loop 层只补齐长期运行能力。

   备选方案是让一个统一 worker 默认处理所有 job type。这样实现更少，但会破坏现有 `embedding-worker-daemon` 规格中“只认领 embedding job”的契约，也会让抓取和 embedding 的资源隔离变差。

3. **Docker Compose 使用独立服务表达进程职责。**

   保留现有 `worker` service 作为 embedding worker，新增 `scheduler` service 和 `crawl-worker` service。每个 service 使用独立 command、healthcheck 和环境变量，便于 home lab 中单独重启和观察。

   备选方案是在一个 shell command 中同时启动 scheduler 与 crawl worker。这样容器数量少，但信号处理、健康检查和日志归因都不清晰。

4. **`start.sh` 默认保持只启动前后端，通过显式环境变量启动后台 daemon。**

   项目约定 `./start.sh` 同时启动后端和前端。为避免本地开发时意外触发抓取，新增 opt-in 开关，例如 `HARVESTER_START_DAEMONS=1` 后才启动 scheduler 与 crawl worker。cleanup 需要追踪所有已启动 PID，确保 Ctrl+C 能停止全部进程。

   备选方案是默认启动所有 daemon。这会更接近生产，但本地开发风险更高，尤其是有真实 source schedule 时会产生网络抓取。

5. **可观测性先用日志、进程健康检查和队列状态，不新增运行状态表。**

   daemon 每轮记录 `scanned/enqueued/skipped/duplicates` 或 `claimed/completed/failed`，Compose healthcheck 用进程匹配验证入口存在，运行结果通过现有 `/queue/status` 和 `/queue/jobs` 查看。第一版不增加 scheduler heartbeat 表，避免为了进程观测引入新 schema。

   备选方案是新增 `daemon_heartbeats` 表。它能提供更强 UI 可见性，但会扩大迁移、API 和前端范围，不是让调度先跑起来的最短路径。

## Risks / Trade-offs

- **[Risk] 多个 scheduler daemon 并发运行会增加数据库扫描和重复 enqueue 尝试。** → Mitigation: 保留 `crawl:<schedule_id>:<window_start>` idempotency key，测试覆盖重复 loop/重复 one-shot 不产生重复 `crawl` job。
- **[Risk] 本地启动 daemon 后误抓真实外部页面。** → Mitigation: `start.sh` 采用显式 opt-in，README 和 `.env.example` 明确默认不会启动 scheduler/crawl worker。
- **[Risk] crawl worker 长期运行中数据库连接泄漏。** → Mitigation: loop 每轮使用 session factory 创建并关闭 session，测试覆盖多轮运行。
- **[Risk] Compose 健康检查只能证明进程存在，不能证明调度真的成功。** → Mitigation: 保留 process healthcheck 作为基础存活检查，新增 smoke/集成测试验证 schedule -> enqueue -> crawl worker 闭环。
- **[Risk] job type 参数扩展后 CLI 行为混乱。** → Mitigation: 默认值保持 `embed_chunks`，无效 job type 直接失败，测试覆盖默认隔离和 crawl 显式入口。

## Migration Plan

1. 先新增 loop 层和 CLI 测试，不改变默认启动行为。
2. 扩展 `worker run --job-type crawl` 与 `scheduler daemon` 命令，验证 one-shot 测试继续通过。
3. 更新 Compose，新增 `scheduler` 与 `crawl-worker` service；保留原 `worker` service。
4. 更新 `start.sh` 的 opt-in daemon 启动和 cleanup 逻辑。
5. 更新 README、`.env.example` 和 smoke 测试。
6. 回滚时停止或删除 `scheduler`/`crawl-worker` service，并不影响现有 API、手动 crawl、schedule 管理和 embedding worker。

## Open Questions

- scheduler daemon 命令最终命名使用 `harvester scheduler daemon` 还是 `harvester scheduler run-loop`。倾向于 `daemon`，因为 `run` 已表示 one-shot。
- Compose 中 scheduler/crawl worker 是否默认启用。倾向于默认启用，因为 Compose 代表 home lab 运行基座；本地 `start.sh` 仍保持 opt-in。
