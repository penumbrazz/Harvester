## ADDED Requirements

### Requirement: 公开抓取策略执行
系统 SHALL 在任何真实抓取请求前执行 public-web fetch policy，并在发现 final URL 或 redirect target 后再次执行校验。

#### Scenario: 拒绝非公网目标
- **WHEN** 抓取目标解析到 loopback、localhost、private、link-local、multicast、reserved 或 unspecified IP 地址空间
- **THEN** 系统 MUST 在创建 raw object 之前拒绝本次抓取

#### Scenario: 拒绝不支持的协议
- **WHEN** 抓取目标使用 `http` 或 `https` 之外的协议
- **THEN** 系统 MUST 拒绝本次抓取，并返回机器可读的 policy reason

#### Scenario: 复检 redirect 目标
- **WHEN** 公开抓取目标 redirect 到不允许的目标
- **THEN** 系统 MUST 将 crawl run 标记为失败，保存拒绝原因，并且不得保存 redirect 后 payload

### Requirement: Firecrawl-compatible 公开抓取 adapter
系统 SHALL 提供真实 Firecrawl-compatible adapter，用于低风险公开网页抓取。

#### Scenario: 成功 adapter 响应
- **WHEN** Firecrawl 返回成功的公开网页响应
- **THEN** adapter MUST 返回归一化 crawl output，包括 original URL、final URL、HTTP status、content type、payload text 和 adapter metadata

#### Scenario: adapter 失败响应
- **WHEN** Firecrawl 返回错误、超时或 malformed output
- **THEN** adapter MUST 返回结构化失败结果，让 crawl run 和 audit log 可以持久化失败原因

#### Scenario: 缺少 Firecrawl 配置
- **WHEN** 请求真实抓取但 Firecrawl URL 或必要配置缺失
- **THEN** 系统 MUST 明确失败，不得回退到 fixture 或 stub 行为

### Requirement: Raw payload archive 存储
系统 SHALL 将真实抓取 payload 写入 archive storage，并且只在 Postgres 中持久化 raw object metadata。

#### Scenario: 保存成功 raw payload
- **WHEN** 公开抓取返回允许且未超过大小限制的 payload
- **THEN** 系统 MUST 将 payload 写入配置的 archive 位置，并创建包含 storage URI、content hash、byte size、content type 和 retention metadata 的 raw object

#### Scenario: payload 不进入 Postgres
- **WHEN** 为真实抓取创建 raw object
- **THEN** 系统 MUST NOT 将 raw payload inline 存入 Postgres

#### Scenario: 拒绝超大 payload
- **WHEN** 抓取 payload 超过配置的最大 byte size
- **THEN** 系统 MUST 将 crawl run 标记为失败，并避免保存超大 payload

### Requirement: Crawl run API 和 CLI 执行
系统 SHALL 暴露 crawl run API 和 CLI 命令，通过 Harvester API 触发真实公开网页抓取。

#### Scenario: 对 approved source 执行抓取
- **WHEN** 已认证用户请求对 approved source 和 approved low-risk recipe 执行 crawl run
- **THEN** 系统 MUST 执行抓取、持久化 crawl run 状态，并在成功时返回 crawl run ID 和 raw object ID

#### Scenario: 拒绝未批准 source 或 recipe
- **WHEN** crawl run 请求指向 candidate source、paused source、missing source、unapproved recipe 或 high-risk recipe
- **THEN** 系统 MUST 拒绝请求，并写入解释拒绝原因的 audit event

#### Scenario: CLI 使用 HTTP API
- **WHEN** 用户运行 CLI crawl 命令
- **THEN** CLI MUST 调用 HTTP API，并且 MUST NOT 直接创建数据库 session

### Requirement: 抓取审计和失败可见性
系统 SHALL 为公开抓取成功、policy 拒绝和 adapter 失败写入 audit 与 failure 记录。

#### Scenario: 成功抓取审计
- **WHEN** 公开抓取成功
- **THEN** 系统 MUST 写入包含 source、recipe、crawl run、final URL 和 raw object 标识符的 audit event

#### Scenario: 失败抓取可见
- **WHEN** 公开抓取因为 policy 拒绝、adapter error、timeout 或 oversized payload 失败
- **THEN** 系统 MUST 将 crawl run 标记为 failed，并写入可通过现有 failure inspection API 查看的一条 error message

### Requirement: CDC 公开抓取 smoke
系统 SHALL 提供显式 CDC public crawl smoke 路径，用于验证真实 crawl-to-search 链路，同时不能让普通 regression tests 依赖网络。

#### Scenario: CDC live smoke opt-in
- **WHEN** 环境配置显式启用 live crawl smoke
- **THEN** CDC smoke MUST 执行真实公开抓取，并验证 raw object metadata、抽取出的 content items、item versions 或 chunks，以及 searchable output

#### Scenario: regression tests 保持确定性
- **WHEN** live crawl smoke 没有显式启用
- **THEN** 普通 regression tests MUST 使用 fixtures 或 adapter fakes，并且 MUST NOT 访问网络
