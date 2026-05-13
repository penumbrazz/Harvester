## 1. Scheduler Daemon Loop

- [x] 1.1 先写 `tests/jobs/test_scheduler_daemon.py`，覆盖 scheduler loop 调用 `run_scheduler_once`、传递 `poll_interval`/`limit`、每轮关闭 session、空轮询 sleep 和 `should_stop` 停止条件。
- [x] 1.2 扩展 `tests/jobs/test_scheduler_daemon.py`，覆盖单轮异常会 rollback、关闭 session、记录错误并继续下一轮。
- [x] 1.3 在 `harvester/jobs/scheduler.py` 中实现 `run_scheduler_loop(session_factory, poll_interval, limit, should_stop=None)`，复用现有 one-shot 调度逻辑，不直接执行抓取。
- [x] 1.4 先写 `tests/cli/test_scheduler_daemon_cli.py`，覆盖 `harvester scheduler daemon --poll-interval --limit` 参数传递、启动提示和 one-shot `harvester scheduler run` 行为保持不变。
- [x] 1.5 在 `harvester/cli/main.py` 中新增 `scheduler daemon` 命令，并保证日志或输出包含 scheduler daemon 身份和每轮统计。
- [x] 1.6 运行 `uv run pytest tests/jobs/test_scheduler_daemon.py tests/cli/test_scheduler_daemon_cli.py tests/cli/test_scheduler_cli.py -q` 并修复失败。

## 2. Crawl Worker Daemon 与 Job Type 隔离

- [x] 2.1 先扩展 `tests/workers/test_daemon.py`，覆盖 crawl worker loop 只处理 `crawl` job、每轮关闭 session、空队列 sleep、`should_stop` 停止条件和异常继续运行。
- [x] 2.2 先扩展 `tests/cli/test_worker_cli.py`，覆盖 `harvester worker run --job-type crawl`、无效 `--job-type` 非零退出、默认 `worker run` 仍只启动 embedding worker。
- [x] 2.3 在 `harvester/workers/daemon.py` 中实现 crawl worker loop，必要时提取共享 loop helper，但保持默认 `run_loop` 的 embedding 语义不变。
- [x] 2.4 在 `harvester/cli/main.py` 中为 `worker run` 增加 `--job-type` 参数，确保 crawl worker 不初始化 embedding adapter。
- [x] 2.5 增加或调整测试，证明默认 `worker once` 和 `worker run` 都不会认领 `crawl` 或 `extract` job。
- [x] 2.6 运行 `uv run pytest tests/workers/test_daemon.py tests/cli/test_worker_cli.py -q` 并修复失败。

## 3. 本地启动与 Compose 编排

- [x] 3.1 先扩展 `tests/deploy/test_compose_config.py`，覆盖 `scheduler` service、`crawl-worker` service、各自 command、`env_file`、`depends_on` 和区分进程角色的 healthcheck。
- [x] 3.2 更新 `docker-compose.yml`，保留现有 `server` 与默认 embedding `worker` service，新增 `scheduler` 和 `crawl-worker` service。
- [x] 3.3 先新增或扩展脚本测试，覆盖 `./start.sh` 默认只启动后端和前端，以及 `HARVESTER_START_DAEMONS=1` 时会启动 scheduler daemon 与 crawl worker daemon。
- [x] 3.4 更新 `start.sh`，用显式 opt-in 启动 scheduler/crawl worker，并让 cleanup 停止所有已启动 PID。
- [x] 3.5 更新 `.env.example`，加入 scheduler/crawl worker poll interval、limit 和本地 daemon opt-in 配置。
- [x] 3.6 运行 `uv run pytest tests/deploy/test_compose_config.py tests/deploy/test_env_example.py tests/deploy/test_smoke_script.py -q` 并修复失败。

## 4. 自动调度闭环验证

- [x] 4.1 先写或扩展集成测试，验证 active 到期 schedule 在 scheduler daemon loop 中自动创建 `crawl` job，随后由 crawl worker daemon loop 处理到现有 crawl execution 结果。
- [x] 4.2 在集成测试中断言 scheduler daemon 只创建 `crawl` job，不直接调用网络抓取 adapter。
- [x] 4.3 在集成测试中断言自动调度结果继续遵守 raw evidence 与 `item_version -> chunk` embedding 分层。
- [x] 4.4 扩展队列观测测试，确认自动调度产生的 job 可通过队列状态或 job 列表观察，且不返回 raw HTML/API payload。
- [x] 4.5 运行 `uv run pytest tests/integration/test_schedule_crawl_pipeline.py tests/cli/test_queue_status_cli.py tests/api/test_job_list.py -q` 并修复失败。

## 5. 文档、Smoke 与最终校验

- [x] 5.1 更新 README 的 Watch Scheduler 章节，区分 one-shot、scheduler daemon、crawl worker daemon、Compose 自动运行和本地 opt-in 启动方式。
- [x] 5.2 更新 smoke 脚本或 smoke 测试，验证 Compose 配置包含 scheduler/crawl worker，并保留 API `8001`、前端 `5173`、omlx 外部 `8000` 端口约定。
- [x] 5.3 确认文档继续强调 scheduler 只创建 `crawl` job，embedding 只能从 `item_version -> chunk` 开始，不能对 raw HTML/API payload 做 embedding。
- [x] 5.4 运行相关后端测试：`uv run pytest tests/jobs/test_scheduler_daemon.py tests/workers/test_daemon.py tests/cli/test_scheduler_daemon_cli.py tests/cli/test_worker_cli.py tests/deploy/test_compose_config.py -q`。
- [x] 5.5 运行全量测试：`uv run pytest -q`，如涉及前端文档或 UI 行为再运行对应 `npm` 测试。
