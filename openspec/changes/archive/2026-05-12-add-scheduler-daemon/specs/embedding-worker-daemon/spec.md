## ADDED Requirements

### Requirement: Embedding worker isolation with scheduler daemons
系统 SHALL 在新增 scheduler daemon 和 crawl worker daemon 后保持 embedding worker 的默认隔离语义。

#### Scenario: 默认 worker run 只处理 embedding job
- **WHEN** 用户运行 `harvester worker run` 且没有指定 `--job-type`
- **THEN** 系统 MUST 只认领和处理 `embed_chunks` job，并保持 `crawl` job 与 `extract` job 不变

#### Scenario: 默认 worker once 只处理 embedding job
- **WHEN** 用户运行 `harvester worker once` 且没有指定 `--job-type`
- **THEN** 系统 MUST 只执行 embedding worker one-shot 逻辑，并保持 `crawl` job 与 `extract` job 不变

#### Scenario: Compose worker service 保持 embedding worker
- **WHEN** 检查 `docker-compose.yml` 中现有 `worker` service
- **THEN** 该 service MUST 继续运行默认 embedding worker daemon，且不能改为消费所有 job type 的通用 worker

#### Scenario: Crawl worker 不初始化 embedding adapter
- **WHEN** 用户运行 `harvester worker run --job-type crawl`
- **THEN** 系统 MUST 启动 crawl worker daemon，且不能要求配置或初始化 embedding adapter

#### Scenario: Extract job 不被新增 daemon 误消费
- **WHEN** 队列中存在 `extract` job，并且只启动 scheduler daemon、crawl worker daemon 和默认 embedding worker
- **THEN** `extract` job MUST 保持 pending，除非用户显式启动对应 extract worker 入口
