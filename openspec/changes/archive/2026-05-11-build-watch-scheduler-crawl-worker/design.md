## Context

当前 Harvester 已经具备手动 crawl 闭环：API/CLI 可以触发 `/crawl/run`，`execute_crawl` 会执行 fetch policy、Firecrawl adapter、raw archive、`raw_object` 元数据和 audit；抽取 pipeline 会创建 `content_item`、`item_version`、`chunk` 和 `embed_chunks` job；worker daemon 已能消费 embedding job。缺口是 watch 层还不会自动把到期的 Source/Topic 转成 crawl job，所以 CDC weekly、Sina 7x24 和 Topic Watch 仍然依赖人工触发。

这个 change 的核心是新增一个轻量调度层，把“何时抓取”从同步 API 调用中拆出来。Harvester 仍然以 Postgres 为事实源，调度器只创建 job，不直接执行抓取；crawl worker 只消费 `crawl` job，并复用现有 `execute_crawl` 的安全边界。

## Goals / Non-Goals

**Goals:**

- 为 Source Watch 和 Topic Watch 增加持久化调度记录。
- 提供 one-shot scheduler，把到期 schedule 幂等地转成 `crawl` job。
- 提供 crawl job handler，使用现有 job lease/retry/dead-letter 机制执行抓取。
- 保证过期 Topic Watch 不再创建新的 crawl job。
- 保证同一 schedule 在同一时间窗口不会重复 enqueue。
- 保持现有 `embed_chunks` worker 行为不变；新增 crawl job 时必须显式选择 crawl job type。

**Non-Goals:**

- 不实现 LightRAG、KG、MCP 或推送。
- 不新增登录态、browser profile、自定义脚本或高风险 recipe 执行能力。
- 不实现自动 source discovery。
- 不替换现有 Firecrawl adapter、extractor 或 embedding pipeline。
- 不要求 scheduler 作为长期守护进程运行；第一版先提供 one-shot，后续由 cron/systemd/Compose 调用。

## Decisions

1. **新增 `watch_schedules` 表，而不是把调度字段塞进 `sources` 或 `topic_sources`。**

   `sources` 描述信息来源，`topic_sources` 描述关联关系；调度是运行策略，后续可能出现同一 source 多个 recipe、同一 source 同时服务固定 watch 和 topic watch。单独表更清晰。

   字段建议：
   - `id`
   - `schedule_key`：稳定唯一键，例如 `source:<source_id>:recipe:<recipe_id>` 或 `topic:<topic_id>:source:<source_id>:recipe:<recipe_id>`
   - `source_id`
   - `topic_watch_id` nullable
   - `recipe_id`
   - `status`: `active | paused | archived`
   - `interval_seconds`
   - `next_run_at`
   - `last_enqueued_at`
   - `priority`
   - `lane`
   - `created_at` / `updated_at`

   替代方案是给 `sources` 增加 `interval_seconds` 和 `next_run_at`。这对固定 source 最省事，但会让 topic-specific schedule 和多 recipe 变得别扭。

2. **scheduler 只创建 job，不直接执行 crawl。**

   `run_scheduler_once(session, now, limit)` 查询到期 schedule，校验 source/topic/recipe 状态，然后调用 `create_job(job_type="crawl", ...)`。这样调度事务很短，不受网络抓取耗时影响，也能复用现有 job lease 和 retry。

   替代方案是在 scheduler 内直接调用 `execute_crawl`。这会让调度器变成长事务和网络执行器，不利于失败隔离。

3. **用 schedule window idempotency key 防重复。**

   `crawl` job 的 `idempotency_key` 使用 `crawl:<schedule_id>:<window_start>`。`window_start` 基于 `next_run_at` 或按 `interval_seconds` 归一化后的时间窗口生成。即使 scheduler 被重复调用，同一个窗口也只会创建一个 job。

   替代方案是只依赖 `next_run_at` 推进。进程崩溃或并发 scheduler 下容易产生重复 job。

4. **crawl worker 作为显式 job type handler 加入，而不是改变 embedding worker 默认行为。**

   现有 `harvester worker once --limit 1` 已经有 embedding worker 语义。为了不破坏既有契约，第一版新增 `--job-type crawl` 或独立 crawl worker 入口；默认仍处理 `embed_chunks`。

   替代方案是让 worker 默认处理所有 job type。这样更接近统一 worker，但会改变现有 embedding worker 行为。

5. **永久失败和可重试失败分开处理。**

   crawl job handler 需要区分：
   - 永久失败：source/recipe 不存在、recipe 未批准、fetch policy 拒绝、高风险 recipe。crawl run 和 audit 保留，job 完成或 dead-letter，但不创建无限 retry。
   - 可重试失败：adapter/network/archive 临时异常。调用 `fail_job` 进入现有 retry/dead-letter 机制。

   如果现有 `execute_crawl` 结果不足以区分错误类型，先在 service 层增加可诊断的 `error_code` / `retryable` 字段，而不是在 handler 中解析错误字符串。

## Risks / Trade-offs

- **[Risk] 调度 schema 过早变复杂。** → Mitigation: 第一版只支持 interval schedule，不支持 cron 表达式、jitter、复杂日历或分布式 scheduler leader election。
- **[Risk] scheduler 并发运行导致重复 job。** → Mitigation: `watch_schedules.schedule_key` 和 `jobs.idempotency_key` 双重约束，scheduler 测试覆盖重复调用。
- **[Risk] 过期 topic 被反复扫描但不 enqueue。** → Mitigation: scheduler 对过期 topic 返回 skipped 计数；后续可增加 topic cooldown/auto-pause，但本 change 不强行改变 topic 状态机。
- **[Risk] crawl job 永久失败进入 retry storm。** → Mitigation: service 层返回 `retryable`，handler 只对可重试错误调用 `fail_job`。
- **[Risk] 同一 source 高频调度压住其他 job。** → Mitigation: 创建 job 时写入 `source_id` 和 lane，继续使用现有 `claim_next_jobs` 的 per-source/per-type fairness。

## Migration Plan

1. 新增 `watch_schedules` 表和索引，迁移不回填默认 schedule。
2. 新增 schedule API/CLI 后，用户显式为 CDC、Sina 或 Topic Source 创建 schedule。
3. 部署 scheduler one-shot 命令；先手动运行验证 enqueue 行为。
4. 部署 crawl worker one-shot；验证 crawl job 通过现有抓取闭环完成。
5. 需要回滚时，停止 scheduler 调用并暂停 crawl worker job type；保留表和已有 job，不影响手动 `/crawl/run` 和 embedding worker。

## Open Questions

- 第一版是否需要 API 管理 schedule，还是只提供 CLI 通过 API 创建 schedule。倾向于提供最小 API，因为 CLI 的状态变更不能直接写库。
- Compose 是否在本 change 中增加 scheduler service，还是先只提供命令和测试。倾向于先提供命令，避免调度频率在未实机验证前固化。
- Sina 7x24 的默认 interval 是否由 seed 数据配置，还是由用户通过 CLI 创建 schedule 时指定。倾向于用户显式指定。
