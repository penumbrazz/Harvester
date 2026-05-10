## 1. Schema 与模型

- [x] 1.1 先写 `tests/db/test_watch_schedules_schema.py`，覆盖表、唯一 `schedule_key`、source/topic/recipe 外键、interval、next_run_at、status 和索引。
- [x] 1.2 新增 Alembic migration，创建 `watch_schedules` 表和必要索引。
- [x] 1.3 在 `harvester/db/models.py` 新增 `WatchSchedule` ORM 模型，保持字段与 migration 一致。
- [x] 1.4 运行 `uv run pytest tests/db/test_watch_schedules_schema.py -q` 并修复失败。

## 2. Schedule API 与 CLI

- [x] 2.1 先写 `tests/api/test_watch_schedules.py`，覆盖创建 source schedule、创建 topic source schedule、重复 schedule、未 approved recipe、无效 source/topic/recipe。
- [x] 2.2 新增 schedule API router，所有状态变更必须校验 API token 并写 audit。
- [x] 2.3 先写 `tests/cli/test_schedule_cli_http_only.py`，证明 CLI 创建 schedule 只调用 HTTP API，不直接创建数据库 session。
- [x] 2.4 在 Typer CLI 中新增 schedule 创建命令，支持 source、可选 topic、recipe、interval 和 next-run 参数。
- [x] 2.5 运行 `uv run pytest tests/api/test_watch_schedules.py tests/cli/test_schedule_cli_http_only.py -q` 并修复失败。

## 3. Scheduler one-shot

- [x] 3.1 先写 `tests/jobs/test_watch_scheduler.py`，覆盖到期 source schedule enqueue、到期 topic schedule enqueue、未到期不 enqueue、过期 topic skipped、非 active topic skipped。
- [x] 3.2 实现 `harvester/jobs/scheduler.py`，提供 `run_scheduler_once(session, now, limit)` 和可测试的统计结果。
- [x] 3.3 为 crawl job 生成稳定 payload、source_id、lane、priority 和 `idempotency_key`。
- [x] 3.4 enqueue 成功或命中重复 job 后推进 `last_enqueued_at` 和 `next_run_at`。
- [x] 3.5 运行 `uv run pytest tests/jobs/test_watch_scheduler.py -q` 并修复失败。

## 4. Scheduler 幂等与并发

- [x] 4.1 扩展 `tests/jobs/test_watch_scheduler.py`，覆盖重复运行 scheduler 只创建一个当前窗口 job。
- [x] 4.2 新增并发或事务级测试，证明同一 schedule/window 的重复 enqueue 会被 job idempotency 约束拦住。
- [x] 4.3 修复 `create_job` 调用或 scheduler 事务边界，确保重复 job 不会推进出错。
- [x] 4.4 运行 `uv run pytest tests/jobs/test_watch_scheduler.py -q` 并修复失败。

## 5. Crawl job handler

- [x] 5.1 先写 `tests/workers/test_crawl_handler.py`，覆盖成功 crawl job、payload 缺失、source/recipe 缺失、未 approved recipe、fetch policy 永久失败、adapter 可重试失败。
- [x] 5.2 调整 `execute_crawl` 结果或异常类型，提供 `error_code` / `retryable` 诊断字段，避免 handler 解析错误字符串。
- [x] 5.3 实现 `process_crawl_job`，解析 payload，调用现有 crawl execution service，并按 retryable 结果 complete 或 fail job。
- [x] 5.4 确保 payload 中的 `topic_watch_id` 写入 crawl run 或下游可追溯 metadata。
- [x] 5.5 运行 `uv run pytest tests/workers/test_crawl_handler.py tests/jobs/test_public_crawl_execution.py -q` 并修复失败。

## 6. Worker 与运维 CLI

- [x] 6.1 先扩展 `tests/workers/test_daemon.py`，覆盖默认 `worker once` 仍只处理 `embed_chunks`，指定 `job_type=crawl` 时只处理 crawl job。
- [x] 6.2 扩展 worker daemon 的 one-shot 入口，支持显式 job type 和 handler 分发，同时保持默认 embedding 行为。
- [x] 6.3 先写 `tests/cli/test_scheduler_cli.py`，覆盖 scheduler one-shot 输出 scanned、enqueued、skipped、duplicate 计数。
- [x] 6.4 实现 scheduler CLI one-shot 命令。
- [x] 6.5 先写 `tests/cli/test_queue_status_cli.py` 或 API 测试，覆盖按 job type/status 聚合队列状态且不返回 raw payload。
- [x] 6.6 实现队列状态查看 API/CLI。
- [x] 6.7 运行 `uv run pytest tests/workers/test_daemon.py tests/cli/test_scheduler_cli.py tests/cli/test_queue_status_cli.py -q` 并修复失败。

## 7. 集成验证与文档

- [x] 7.1 新增集成测试，验证创建 schedule -> scheduler enqueue -> crawl worker 处理 -> raw object 可追溯的闭环。
- [x] 7.2 更新 README 的本地运行说明，加入 schedule 创建、scheduler one-shot、crawl worker one-shot 和队列状态示例。
- [x] 7.3 确认文档继续强调 `raw_object` 是短保留 evidence，embedding 只从 `item_version -> chunk` 开始。
- [x] 7.4 运行相关测试：`uv run pytest tests/db/test_watch_schedules_schema.py tests/api/test_watch_schedules.py tests/jobs/test_watch_scheduler.py tests/workers/test_crawl_handler.py tests/integration -q`。
- [x] 7.5 运行全量测试：`uv run pytest -q`。
