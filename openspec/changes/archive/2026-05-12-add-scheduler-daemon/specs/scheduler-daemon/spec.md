## ADDED Requirements

### Requirement: Scheduler daemon execution
系统 SHALL 提供长期运行的 scheduler daemon，用于周期性扫描到期 watch schedule 并创建 `crawl` job。

#### Scenario: 启动 scheduler daemon
- **WHEN** 用户运行 `harvester scheduler daemon --poll-interval 5 --limit 20`
- **THEN** 系统 MUST 以 5 秒轮询间隔重复调用现有调度 one-shot 逻辑，并且每轮最多处理 20 个到期 schedule

#### Scenario: Scheduler daemon 每轮释放数据库 session
- **WHEN** scheduler daemon 完成一轮扫描、入队或错误处理
- **THEN** 系统 MUST 关闭该轮使用的数据库 session，避免长期运行时连接泄漏

#### Scenario: Scheduler daemon 记录每轮统计
- **WHEN** scheduler daemon 完成一轮调度
- **THEN** 系统 MUST 记录或输出 `scanned`、`enqueued`、`skipped` 和 `duplicates` 统计，且日志中 MUST 能识别该进程是 scheduler daemon

#### Scenario: Scheduler daemon 单轮失败后继续运行
- **WHEN** scheduler daemon 某一轮调度抛出未处理异常
- **THEN** 系统 MUST 回滚并关闭当前 session，记录可诊断错误，并在下一次 poll interval 后继续运行

#### Scenario: One-shot scheduler 行为保持不变
- **WHEN** 用户运行 `harvester scheduler run`
- **THEN** 系统 MUST 只执行一次调度扫描、输出统计并退出

### Requirement: Crawl worker daemon execution
系统 SHALL 提供长期运行的 crawl worker daemon，用于持续消费 `crawl` job 并复用现有 crawl job handler。

#### Scenario: 启动 crawl worker daemon
- **WHEN** 用户运行 `harvester worker run --job-type crawl --poll-interval 5 --limit 10`
- **THEN** 系统 MUST 重复认领并处理 `crawl` job，每轮最多处理 10 个 job，并在空队列时按 5 秒轮询间隔等待

#### Scenario: Crawl worker daemon 只认领 crawl job
- **WHEN** 队列中同时存在 `crawl`、`embed_chunks` 和 `extract` job
- **THEN** crawl worker daemon MUST 只认领和处理 `crawl` job，并保持其他 job type 不变

#### Scenario: Crawl worker daemon 每轮释放数据库 session
- **WHEN** crawl worker daemon 完成一轮 job 处理或错误处理
- **THEN** 系统 MUST 关闭该轮使用的数据库 session，避免长期运行时连接泄漏

#### Scenario: Crawl worker daemon 记录每轮统计
- **WHEN** crawl worker daemon 完成一轮处理
- **THEN** 系统 MUST 记录或输出 `claimed`、`completed` 和 `failed` 统计，且日志中 MUST 能识别该进程是 crawl worker daemon

#### Scenario: 无效 worker job type 被拒绝
- **WHEN** 用户运行 `harvester worker run --job-type unknown`
- **THEN** CLI MUST 返回非零退出码并显示可读错误，且不能启动任何 worker loop

### Requirement: Runtime process orchestration
系统 SHALL 在本地开发脚本和 Docker Compose 部署中提供清晰的 scheduler 与 crawl worker 进程编排。

#### Scenario: Compose 启动 scheduler service
- **WHEN** 检查 `docker-compose.yml`
- **THEN** 文件 MUST 定义 `scheduler` service，命令 MUST 启动 `harvester scheduler daemon` 或等价 scheduler daemon 入口，并复用项目 `.env` 配置

#### Scenario: Compose 启动 crawl worker service
- **WHEN** 检查 `docker-compose.yml`
- **THEN** 文件 MUST 定义 `crawl-worker` service，命令 MUST 启动 `harvester worker run --job-type crawl` 或等价 crawl worker daemon 入口，并复用项目 `.env` 配置

#### Scenario: Compose healthcheck 区分进程角色
- **WHEN** 检查 `scheduler`、`crawl-worker` 和 `worker` service 的 healthcheck
- **THEN** 每个 healthcheck MUST 匹配对应 daemon 入口，且不能把 scheduler、crawl worker 和 embedding worker 混为同一个进程检查

#### Scenario: 本地 start 脚本默认不启动后台 daemon
- **WHEN** 用户直接运行 `./start.sh`
- **THEN** 脚本 MUST 只启动 Harvester API 和前端 dev server，保持当前本地开发默认行为

#### Scenario: 本地 start 脚本可显式启动后台 daemon
- **WHEN** 用户设置 `HARVESTER_START_DAEMONS=1` 后运行 `./start.sh`
- **THEN** 脚本 MUST 同时启动 scheduler daemon 和 crawl worker daemon，并在 Ctrl+C 或退出时停止所有已启动进程

#### Scenario: 环境变量文档化
- **WHEN** 检查 `.env.example` 和 README
- **THEN** 文档 MUST 包含 scheduler/crawl worker poll interval、每轮 limit 和本地 daemon opt-in 开关说明

### Requirement: Automatic scheduling pipeline
系统 SHALL 支持无需人工 one-shot 命令的自动调度闭环。

#### Scenario: 到期 schedule 自动入队并被处理
- **WHEN** 存在 active 且到期的 watch schedule，并且 scheduler daemon 与 crawl worker daemon 正在运行
- **THEN** 系统 MUST 自动创建 `crawl` job，并由 crawl worker daemon 处理到现有 crawl execution 结果

#### Scenario: Scheduler daemon 不直接执行网络抓取
- **WHEN** scheduler daemon 扫描到到期 schedule
- **THEN** 系统 MUST 只创建 `crawl` job，不能在 scheduler daemon 进程内直接调用网络抓取 adapter

#### Scenario: 自动调度保留 raw evidence 分层
- **WHEN** 自动调度触发 crawl job 并成功抓取页面
- **THEN** 系统 MUST 按现有 pipeline 保存 raw evidence 和后续 content item 抽取，且 embedding MUST 只从 `item_version -> chunk` 开始

#### Scenario: 队列观测不暴露 raw payload
- **WHEN** 用户通过队列状态或 job 列表观察自动调度产生的 job
- **THEN** 系统 MUST 提供 job type、status、lane、source 和时间等运维信息，并且不能返回 raw HTML/API payload

### Requirement: Scheduler daemon backpressure and idempotency
系统 SHALL 在长期运行模式下保留现有调度幂等、防重复和基础背压能力。

#### Scenario: Poll interval 和 limit 控制调度压力
- **WHEN** scheduler daemon 使用指定 `poll_interval` 和 `limit` 运行
- **THEN** 系统 MUST 按这些参数限制扫描频率和每轮处理数量

#### Scenario: 重复 scheduler daemon 不产生重复 crawl job
- **WHEN** 两个 scheduler daemon 或连续两轮调度处理同一个 schedule window
- **THEN** 系统 MUST 依赖稳定 idempotency key 确保同一 schedule window 最多创建一个 `crawl` job

#### Scenario: 不可运行 schedule 不入队
- **WHEN** schedule 处于 `paused`、`disabled`，或关联 source/topic/recipe 不可运行
- **THEN** scheduler daemon MUST 不创建 `crawl` job，并记录 skipped 或可诊断状态
