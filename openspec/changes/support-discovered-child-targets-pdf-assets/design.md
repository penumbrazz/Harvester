## Context

Harvester 当前已经有 Source、Recipe、Watch Schedule、Job、Crawl Run、Raw Object、Content Item、Item Version、Chunk 和 embedding worker 的基础闭环。现有 `execute_crawl` 以 `source.url` 为唯一抓取目标，抓取成功后保存 raw payload archive、创建 `raw_object`，再入队 `extract` job。这个模型适合固定页面或 API feed，但不适合“固定入口页发布动态详情页，详情页再发布 PDF 全文”的来源。

中国疾控中心流感周报是典型例子：

```text
固定 Source URL
https://www.chinacdc.cn/jksj/jksj04_14249/
        │
        ▼
列表页发现每周详情页
/jksj/jksj04_14249/202605/t20260508_1835622.html
        │
        ▼
详情页发现 PDF 附件
*.pdf
        │
        ▼
PDF 文本才是最完整的资料正文
```

这个 change 不应把每个动态详情页建成 Source，也不应引入无边界递归 crawler。Harvester 的控制面目标更适合“固定 Source + 受控 target discovery + 分阶段 evidence”的设计。

## Goals / Non-Goals

**Goals:**

- 支持从固定 Source 入口页发现详情页和 PDF asset URL。
- 持久化 discovered target 的角色、状态、父子关系、深度、幂等键和最近观察时间。
- 通过现有 job queue、crawl worker、fetch policy、archive 和 extraction pipeline 处理 discovered target。
- 让列表页、详情页和 PDF 都各自成为 `raw_object` evidence，但长期搜索内容只从抽取出的 `content_item` / `item_version` / `chunk` 开始。
- 支持 CDC 流感周报这一类 list -> detail -> pdf 的确定性 fixture 和可选 live smoke 验证。
- 保留 source frontier / rewind / dedup 思路：可重复观察旧条目，数据库唯一键和 content hash 保证幂等。

**Non-Goals:**

- 不实现通用网站递归爬取、站点地图全量抓取或跨域爬虫。
- 不支持登录态、浏览器 profile、验证码、脚本执行或高风险 recipe。
- 不把 PDF 原始 bytes 或 HTML payload inline 写入 Postgres。
- 不对 raw HTML 或 raw PDF payload 做 embedding。
- 不要求第一版支持所有 PDF 格式的完美解析；解析失败必须可诊断并保留 raw evidence。

## Decisions

1. **新增 `crawl_targets` 持久化模型，而不是把动态 URL 建成 Source。**

   Source 继续代表一个被管理的信息源，例如“CDC 流感周报”。`crawl_targets` 表示这个 Source 下待抓取或已抓取的具体 URL。

   建议字段：

   ```text
   id
   source_id
   recipe_id
   parent_target_id nullable
   discovered_from_raw_object_id nullable
   target_url
   final_url nullable
   canonical_url
   canonical_url_hash
   target_role = list | detail | asset
   media_type = html | pdf | unknown
   external_item_id nullable
   status = pending | running | completed | failed | skipped
   depth
   priority
   last_raw_object_id nullable
   failure_count
   last_error nullable
   first_seen_at
   last_seen_at
   created_at / updated_at
   ```

   唯一键建议为 `(source_id, target_role, canonical_url_hash)`；如果某些源能稳定生成 `external_item_id`，content item 仍以 `(source_id, external_item_id)` 为权威资料身份。

   替代方案是把 target 信息放进 job payload。实现更快，但 job 完成后缺少可审计状态，不利于重试、去重、前端观察和父子关系追踪。

2. **抓取执行支持可选 target，但保留 Source 安全边界。**

   `crawl` job 可以继续支持旧 payload：

   ```json
   {"source_id": "...", "recipe_id": "..."}
   ```

   同时支持 target payload：

   ```json
   {"source_id": "...", "recipe_id": "...", "target_id": "..."}
   ```

   没有 `target_id` 时抓 `source.url` 并可创建 list target；有 `target_id` 时抓 `crawl_targets.target_url`。两条路径都必须通过 Source/Recipe 状态校验、recipe scope 校验、public fetch policy 和 redirect/final URL 复检。

   替代方案是新增 `crawl_target` job type。短期会让 worker dispatch 更清晰，但会重复现有 crawl retry/dead-letter 逻辑；第一版复用 `crawl` job 更稳。

3. **Recipe config 负责限制发现范围。**

   Recipe 不只是 executor 配置，还应描述“允许发现什么”。建议配置结构：

   ```yaml
   discovery:
     enabled: true
     max_depth: 2
     max_targets_per_run: 20
     allowed_hosts:
       - www.chinacdc.cn
     allowed_path_prefixes:
       - /jksj/jksj04_14249/
     allowed_content_types:
       - text/html
       - application/pdf
     list:
       detail_link_selector: "..."
       item_identity_regex: "..."
       rewind_items: 10
     detail:
       pdf_link_selector: "a[href$='.pdf']"
     content_priority:
       - pdf
       - detail_html
   ```

   发现器只能 enqueue 符合 allowlist、深度和数量上限的 target。即使链接来自可信页面，也不能绕过 fetch policy。

   替代方案是把发现规则硬编码进 CDC extractor。CDC 第一版可以有站点专用 extractor，但 scope、depth 和 content type 限制应是通用 recipe 语义，否则后续每个站点都会重新实现安全边界。

4. **列表页和详情页 extractor 可以创建/更新 content item，但 PDF 是优先版本来源。**

   列表页 extractor 的职责是发现条目身份、详情 URL 和摘要：

   ```text
   external_item_id = cncdc-flu-weekly:2026:W18:issue-907
   title = 中国流感监测周报
   observed_url = list URL
   detail target = detail URL
   ```

   详情页 extractor 的职责是补充 metadata、观察详情 URL、发现 PDF target。PDF extractor 抽出的文本才创建最高优先级 `item_version`。如果 PDF 不存在或解析失败，详情页正文可以作为 fallback 版本，但需要在 metadata/audit 中标识来源。

   替代方案是把列表页或详情页直接当作完整文章。这样实现简单，但会把索引页和摘要页混入资料库，搜索质量差，也违背“瀑布流、时间线、搜索结果页不能整体当成一篇文档”的项目约束。

5. **PDF 使用原始 bytes archive + 文本抽取器。**

   当前 Firecrawl adapter 输出 `payload_text`，适合 HTML/markdown，不适合作为 PDF 原始 evidence。PDF target 应支持 binary fetch 结果，archive 写入原始 bytes，`raw_objects.content_type` 记录 `application/pdf`。PDF extractor 从 archive 读取 bytes 后抽取文本。

   Python 依赖建议优先选择 `pypdf`，因为它纯 Python、部署成本低，适合第一版。如果后续遇到扫描版 PDF 或复杂布局，再单独评估 OCR 或 `pymupdf`。

   替代方案是让 Firecrawl 直接返回 PDF markdown。那可以作为增强路径，但不能替代 raw PDF evidence，因为 Harvester 需要可审计原始抓取证据。

6. **target discovery 和下游 job 在同一事务内创建。**

   extraction 发现新 target 时，应在同一事务中 upsert `crawl_targets` 并创建幂等 `crawl` job：

   ```text
   idempotency_key = crawl-target:<target_id>:<canonical_url_hash>
   ```

   如果 target 已存在，则更新 `last_seen_at`、父 raw object observation 和必要 metadata，不创建重复 job，除非 recipe/frontier 判断需要 rewind 或 refetch。

   替代方案是先完成 extraction，再异步扫描 raw object 发现 target。那会降低主流程耦合，但第一版会多一层 worker 和更多失败状态；当前项目已有 stage-local transaction 习惯，先复用即可。

## Risks / Trade-offs

- **[Risk] 发现器不小心变成开放爬虫** → Mitigation: recipe 必须配置 allowed hosts/path prefixes/content types、max depth、max targets per run；所有发现 URL 仍执行 fetch policy。
- **[Risk] PDF 文件较大导致 archive 膨胀或 worker 阻塞** → Mitigation: 使用现有 `HARVESTER_MAX_PAYLOAD_BYTES`，PDF 可配置更低默认上限，超限时记录 failed target 和 crawl run。
- **[Risk] PDF 文本抽取质量不稳定** → Mitigation: 保留 raw PDF evidence；抽取失败不删除 raw object；失败进入可诊断状态，后续可替换 parser 或加入 OCR。
- **[Risk] 一个 content item 被详情页和 PDF 生成重复版本** → Mitigation: `external_item_id` 统一资料身份，`content_priority` 决定版本来源，`content_hash` 防止重复 version。
- **[Risk] target 表引入新的状态机复杂度** → Mitigation: 第一版状态保持最小，只覆盖 pending/running/completed/failed/skipped，并让 crawl run/job 继续承担执行细节。

## Migration Plan

1. 新增 `crawl_targets` 表和索引，不回填历史数据。
2. 扩展 recipe config 校验和 fixture，先支持 CDC list/detail/pdf 结构。
3. 扩展 crawl job handler 支持 `target_id`，保持无 target payload 的旧 Source crawl 行为不变。
4. 扩展 extraction service 允许 extractor 返回 candidate items 和 discovered targets，并在同一事务中 upsert target、创建 crawl job。
5. 新增 PDF binary fetch/archive 路径和 PDF text extractor。
6. 增加 deterministic fixture tests，再增加 opt-in CDC live smoke。
7. 回滚时可暂停发现型 recipe 或删除 schedule；已保存的 raw objects、content items 和 item versions 继续可审计。

## Open Questions

- 第一版是否要在管理控制台展示 `crawl_targets` 列表，还是只在 jobs/crawls 运维页面露出 target 摘要。倾向后者，避免扩大前端范围。
- PDF fetch 是否复用 Firecrawl endpoint 还是新增 direct public HTTP asset fetcher。倾向新增窄接口 binary fetcher，并复用同一 fetch policy。
- CDC 周报的 `external_item_id` 应优先从标题期号解析，还是从详情页 URL 生成。倾向从标题中的年份、周数和期号生成，URL 仅作为 fallback。
