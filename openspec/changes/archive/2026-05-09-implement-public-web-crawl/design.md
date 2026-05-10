## Context

当前 Harvester 已完成控制平面 schema、API/CLI 状态机、Postgres job/frontier、raw object metadata、抽取、去重、chunk/search 和 fixture smoke。真实抓取仍未实现：`StubFirecrawlAdapter` 只从 fixture map 返回内容，CLI 也没有 `crawl run` 入口。

这次变更是从“可测试的资料库骨架”进入“真实公开网页抓取”的第一步。目标不是一次性支持所有站点，而是让低风险公开网页先跑通：

```text
approved source + approved recipe
  -> fetch policy
  -> Firecrawl-compatible adapter
  -> archive raw payload
  -> raw_object metadata
  -> crawl_run status/audit
  -> extractor
  -> content_item / observation / item_version / chunk
  -> search
```

Harvester 运行在 home lab 内网，真实抓取入口必须默认防守。即使第一版只给个人使用，也不能让 agent 通过 API/CLI 抓取 `localhost`、private IP、link-local、NAS、路由器或 Firecrawl 管理口。

## Goals / Non-Goals

**Goals:**

- 实现真实 Firecrawl-compatible HTTP adapter，支持公开网页抓取。
- 实现最小 fetch policy：协议、DNS/IP 分类、redirect 目标、超时、最大响应大小和失败原因。
- 增加 crawl API/CLI 入口，通过 HTTP API 触发状态变更，CLI 不直接写数据库。
- 将 raw payload 写入本地 archive 目录，`raw_objects` 只保存 metadata/hash/storage URI。
- 创建并更新 `crawl_runs`，成功时关联 `raw_object_id`，失败时记录 `error_message`。
- 为 policy 拒绝、adapter 失败、抓取成功写入 `audit_events`。
- 复用现有 CDC fixture extractor，打通至少一个公开网页 raw-to-search smoke。
- 保持 regression tests 默认不访问网络；真实网络 smoke 必须显式开启。

**Non-Goals:**

- 不支持登录态、cookie/browser profile、微博/X/小红书等高风险站点。
- 不支持 custom script executor。
- 不实现 LightRAG、KG 或 MCP adapter。
- 不做完整分布式 worker daemon；可以先实现同步 API/CLI crawl run，再保留 job 化接口。
- 不把 raw HTML/API payload 存进 Postgres。

## Decisions

1. **先做同步 crawl run，再复用 job 表做后续异步化。**
   - 选择：`POST /crawl/run` 先在 API 请求内完成单次低风险抓取和入库，返回 crawl run 结果。
   - 原因：真实公开网页 MVP 需要先验证端到端数据边界。同步实现更容易测试，也能让 CLI 立即可用。
   - 替代方案：直接实现 worker daemon。这个方向长期正确，但会把调度、lease、worker lifecycle 和真实抓取混在一个 change 里，范围过大。

2. **fetch policy 是独立 domain service，API 和 adapter/job 都必须调用。**
   - 选择：新增 `harvester/domain/fetch_policy.py`，返回 allow/deny 结果和机器可读 reason。
   - 原因：不能只在 API 层检查 URL 字符串。adapter 执行时仍要校验最终请求目标和 redirect 后目标。
   - 替代方案：把校验写进 Firecrawl adapter。这样 CLI/API 或未来 worker 很容易绕过同一规则。

3. **默认只允许 public `http`/`https`，DNS 解析后拒绝非公网地址。**
   - 选择：拒绝 `localhost`、loopback、private、link-local、multicast、reserved、unspecified 地址，拒绝非 HTTP 协议。
   - 原因：Harvester 部署在内网，SSRF 风险真实存在。字符串级黑名单不够，必须看解析后的 IP。
   - 替代方案：只依赖 allowlist。allowlist 长期有价值，但第一版样例需要抓 CDC/Sina 这类公开域名，公网默认允许加内网默认拒绝更实用。

4. **raw payload 写 archive，metadata 写 Postgres。**
   - 选择：新增 archive writer，按日期/source/crawl_run 写文件，记录 `storage_uri`、`content_hash`、`byte_size`、`content_type`。
   - 原因：符合现有架构约束，`raw_object` 是短保留 evidence cache，不是长期语料库。
   - 替代方案：把 payload 放进 `raw_objects` JSONB/Text。实现快，但会破坏现有 schema 决策，也会让数据库膨胀。

5. **Firecrawl adapter 使用配置化 base URL/API key，不直接绑定 SaaS。**
   - 选择：沿用 `.env.example` 中已有的 `FIRECRAWL_API_URL`，并补充可选 API key、scrape path、timeout、max bytes。
   - 原因：用户已有 self-host Firecrawl，生产路径应该优先兼容内网部署。
   - 替代方案：直接依赖 cloud endpoint。和 home lab 目标不一致。

6. **CDC live smoke 显式开启，普通测试继续 fixture-first。**
   - 选择：regression tests 使用 stub/monkeypatch；live smoke 通过环境变量如 `HARVESTER_ENABLE_LIVE_CRAWL=1` 才跑。
   - 原因：CI 和本地回归不能依赖外网稳定性，但项目仍需要可执行的真实抓取验证。
   - 替代方案：默认跑 live crawl。会产生慢测试和网络不稳定失败。

## Risks / Trade-offs

- **[Risk] 同步 crawl run 请求可能变慢** → Mitigation: 第一版限制 timeout 和 payload size，只用于低频公开网页；后续 worker daemon 复用同一 execution service。
- **[Risk] Firecrawl 返回结构和 self-host 版本差异** → Mitigation: adapter 做窄接口归一化，只输出 `final_url`、`status_code`、`content_type`、`payload_text`、`metadata`。
- **[Risk] DNS rebinding 或 redirect 绕过 policy** → Mitigation: 请求前解析校验，redirect 后最终 URL 重新校验；如果 adapter 暴露 redirect chain，则逐跳校验。
- **[Risk] CDC 页面结构变化导致 smoke 失败** → Mitigation: live smoke 只作为显式验证；regression 仍依赖 fixture。
- **[Risk] archive 文件增长** → Mitigation: 使用现有 retention metadata，默认 raw payload 7 天保留，后续 cleanup job 可以删除或压缩 payload。

## Migration Plan

1. 新增配置项但保持默认不强制启动真实抓取。未配置 Firecrawl 时，API 返回明确错误，不影响 health/source/topic/fixture/search 测试。
2. 新增 crawl router/CLI 命令，不修改现有 source/recipe/topic 行为。
3. 新增 archive 目录配置，默认可落到本地 `.harvester/archive` 或环境变量指定路径。
4. 部署时先跑 fixture tests，再设置 Firecrawl URL/API key，手动执行 CDC live smoke。
5. 回滚时可以禁用 crawl API 或移除 Firecrawl 配置；已写入的 raw_object metadata 和 archive 文件保持可审计。

## Open Questions

- self-host Firecrawl 当前具体 API shape 是 `/v1/scrape`、`/scrape` 还是其他兼容端点，需要实现时用 adapter config 支持可调 path。
- CDC live 第一版是否抓详情页，还是先只抓列表页并抽取详情链接。建议先列表页入 raw_object，详情页作为后续 per-item crawl task。
- archive URI 是否用 `file://` 还是相对路径。建议 DB 保存 `file://` 绝对 URI，方便 smoke 和诊断。
