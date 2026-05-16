## ADDED Requirements

### Requirement: Discovered target persistence
系统 SHALL 将固定 Source 入口页发现出的动态子页面和资产 URL 持久化为可审计的 crawl target，而不是创建新的 Source。

#### Scenario: 保存新发现的详情页 target
- **WHEN** 列表页抽取器从 approved Source 的 raw object 中发现符合 recipe scope 的详情页 URL
- **THEN** 系统 MUST 创建或更新一个关联该 Source 的 crawl target，并记录 target URL、canonical URL hash、target role、depth、父 raw object、first seen 和 last seen 时间

#### Scenario: 重复发现同一 target
- **WHEN** 后续抓取再次发现同一 Source、target role 和 canonical URL hash 的 target
- **THEN** 系统 MUST 更新既有 target 的 last seen 信息，并且 MUST NOT 创建重复 target

#### Scenario: 动态子页面不变成 Source
- **WHEN** 系统发现详情页或 PDF asset URL
- **THEN** 系统 MUST 保持原有 Source 作为信息源边界，并且 MUST NOT 为该动态 URL 自动创建 Source

### Requirement: Recipe-scoped target discovery
系统 SHALL 使用 approved recipe config 限制 target discovery 的 URL 范围、深度、数量和 content type。

#### Scenario: 允许 scope 内链接
- **WHEN** 抽取器发现的 URL host、path prefix、depth 和 content type 均符合 recipe discovery scope
- **THEN** 系统 MUST 允许该 URL 被 upsert 为 crawl target 并可创建下游 crawl job

#### Scenario: 拒绝 scope 外链接
- **WHEN** 抽取器发现的 URL 不符合 recipe 的 allowed hosts、allowed path prefixes、allowed content types、max depth 或 max targets per run 限制
- **THEN** 系统 MUST 跳过该 target，记录可诊断原因，并且 MUST NOT 创建抓取 job

#### Scenario: 发现 URL 仍执行 fetch policy
- **WHEN** 符合 recipe scope 的 discovered target 准备抓取
- **THEN** 系统 MUST 在抓取前执行 public-web fetch policy，并在 final URL 或 redirect target 变化后再次校验

### Requirement: Target crawl job execution
系统 SHALL 通过现有 `crawl` job 和 crawl worker 处理 discovered target 抓取。

#### Scenario: Target job 抓取 target URL
- **WHEN** crawl worker 处理 payload 包含 `target_id` 的 `crawl` job
- **THEN** 系统 MUST 加载 target、Source 和 Recipe，抓取 target URL，并将成功结果保存为 raw object

#### Scenario: Source crawl 行为保持兼容
- **WHEN** crawl worker 处理不包含 `target_id` 的既有 Source crawl job
- **THEN** 系统 MUST 保持现有抓取 `source.url` 的行为

#### Scenario: Target 抓取状态同步
- **WHEN** target crawl 成功、失败或被 policy 拒绝
- **THEN** 系统 MUST 更新 crawl target 状态、last raw object、failure count 或 last error，并保留 crawl run 与 audit 记录

#### Scenario: Target job 幂等
- **WHEN** extraction 或 scheduler 重复尝试为同一 target 创建 crawl job
- **THEN** 系统 MUST 使用稳定 idempotency key 防止同一 target 在同一抓取窗口重复入队

### Requirement: Multi-stage list detail asset pipeline
系统 SHALL 支持 list -> detail -> asset 的多阶段 raw evidence 链路。

#### Scenario: 列表页发现详情页
- **WHEN** 列表页 raw object 被抽取
- **THEN** 系统 MUST 能创建或更新 content item 身份，并为符合 scope 的详情页创建 detail target

#### Scenario: 详情页发现 PDF asset
- **WHEN** 详情页 raw object 被抽取且页面包含符合 scope 的 PDF 链接
- **THEN** 系统 MUST 为 PDF 链接创建 asset target，并关联到同一 content item 或同一外部资料身份

#### Scenario: 父子 evidence 可追溯
- **WHEN** 用户或系统检查由 PDF 生成的 item version
- **THEN** 系统 MUST 能追溯到 PDF raw object、详情页 target、列表页 observation 和原始 Source

### Requirement: Frontier and dedup integration for discovered targets
系统 SHALL 将 frontier 作为发现范围优化，将数据库唯一键和 content hash 作为幂等权威。

#### Scenario: Rewind 重新观察旧条目
- **WHEN** 列表页抓取因 rewind window 再次观察到旧详情页
- **THEN** 系统 MUST 允许更新 observation 和 last seen，同时依赖 target 唯一键防止重复 target

#### Scenario: URL 变化但资料身份稳定
- **WHEN** 同一期周报的详情 URL 或 PDF URL 发生变化，但 extractor 能解析出相同 external item ID
- **THEN** 系统 MUST 将其归入同一个 content item，并通过 item version content hash 判断是否创建新版本
