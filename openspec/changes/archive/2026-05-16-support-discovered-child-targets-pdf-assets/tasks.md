## 1. 数据模型与迁移

- [x] 1.1 为 `crawl_targets` 编写数据库 schema 测试，覆盖字段、外键、状态、唯一键和查询索引
- [x] 1.2 新增 Alembic 迁移，创建 `crawl_targets` 表、唯一约束和常用索引
- [x] 1.3 新增 SQLAlchemy `CrawlTarget` 模型，并保持与迁移字段一致
- [x] 1.4 添加 target 状态常量或轻量状态转换测试，覆盖 pending、running、completed、failed、skipped

## 2. Target Repository 与 Recipe Scope

- [x] 2.1 为 target URL canonicalization、upsert 幂等和 last seen 更新编写单元测试
- [x] 2.2 实现 `crawl_targets` repository/helper，支持按 Source、role、canonical URL hash upsert 和查询
- [x] 2.3 为 recipe discovery scope 校验编写测试，覆盖 allowed hosts、path prefixes、content types、max depth 和 max targets per run
- [x] 2.4 实现 discovery scope parser/validator，并让 scope 外 target 返回可诊断跳过原因

## 3. Crawl Job 与 Raw Evidence

- [x] 3.1 为 `crawl` job payload 包含 `target_id` 的处理路径编写 worker/service 测试
- [x] 3.2 扩展 crawl job handler，加载 target 并调用 target URL 抓取，同时保持无 `target_id` 的 Source crawl 兼容行为
- [x] 3.3 扩展 crawl execution，使 target 抓取成功后更新 target 状态、last raw object、final URL 和 audit
- [x] 3.4 为 target 抓取失败、policy 拒绝、redirect 拒绝和 retry/dead-letter 行为补充测试
- [x] 3.5 为 target crawl job idempotency key 编写测试，并防止同一 target 重复入队

## 4. Discovery Extractor Contract

- [x] 4.1 扩展 extractor contract 测试，使 extractor 能同时返回 candidate items 和 discovered targets
- [x] 4.2 实现 discovery result 数据结构，保持现有 extractor 兼容
- [x] 4.3 扩展 extraction service，在同一事务中 upsert content item、observation、discovered target 和下游 crawl job
- [x] 4.4 为列表页重复观察、rewind 旧条目和 URL 变化但 external item ID 稳定的场景补充测试

## 5. CDC 周报 List/Detail 发现

- [x] 5.1 新增 CDC 周报列表页 fixture 和预期结果，覆盖详情页 URL、标题、发布日期、期号和 external item ID
- [x] 5.2 实现 CDC 周报列表页 extractor，发现 detail target 并创建或更新 content item 身份
- [x] 5.3 新增 CDC 周报详情页 fixture 和预期结果，覆盖 PDF asset URL 发现
- [x] 5.4 实现 CDC 周报详情页 extractor，补充 observation 并发现 PDF asset target
- [x] 5.5 更新 extractor registry，使 CDC 周报列表页、详情页和 PDF target 能匹配正确 extractor

## 6. PDF 抓取与文本抽取

- [x] 6.1 增加 PDF binary fetch/archive 测试，覆盖 content type、bytes hash、payload size limit 和 raw payload 不入库
- [x] 6.2 实现 PDF target 的 binary fetch 路径，并复用 public-web fetch policy、archive writer 和 crawl run 记录
- [x] 6.3 添加 PDF 解析依赖和文本抽取单元测试，覆盖正常 PDF、空文本 PDF、损坏 PDF 和加密 PDF
- [x] 6.4 实现 PDF extractor，从 archive bytes 抽取 normalized text，并在失败时记录 extraction failure
- [x] 6.5 确保 PDF item version 创建后走现有 chunking 和 embedding job 创建逻辑
- [x] 6.6 实现 recipe content priority，使 PDF 文本优先于详情页 HTML fallback

## 7. 端到端测试与可观测性

- [x] 7.1 编写 CDC fixture 端到端测试，验证 list -> detail -> PDF -> content item -> item version -> chunk -> embedding job
- [x] 7.2 编写 target 可追溯性测试，验证搜索结果可追溯到 PDF raw object、detail target、list observation 和 Source
- [x] 7.3 增加 opt-in CDC live smoke，默认禁用真实网络访问
- [x] 7.4 扩展 jobs/crawls 或 failures API schema，使运维视图可看到 target 摘要、状态和错误，但不暴露 raw payload
- [x] 7.5 为新增 API 字段补充后端测试和前端类型测试；如触及前端页面，先按 `DESIGN.md` 校验视觉和交互约束

## 8. 文档与验证

- [x] 8.1 更新 README，说明固定 Source、discovered target、PDF raw evidence 和 CDC 周报配置示例
- [x] 8.2 更新 `.env.example`，补充 PDF/target 相关 payload limit 或 live smoke opt-in 配置
- [x] 8.3 运行相关后端测试：`uv run pytest tests/db tests/jobs tests/extractors tests/integration -q`
- [x] 8.4 如修改前端，运行 `npm run lint`、相关 Vitest 和 E2E 测试
- [x] 8.5 运行 `openspec status --change support-discovered-child-targets-pdf-assets`，确认 change 可实施
