---
name: harvester-source-onboarding
description: 新增、修改或测试 Harvester 抓取源时使用；包括 source、recipe、schedule、extractor、发现规则、fixture、特定来源抓取行为、单次抓取、试跑、爬一下、下载公开网页或 PDF。
---

# Harvester 来源接入

## 目的

当用户要求添加新的抓取来源、添加新的采集 URL、修改来源专用 extractor、变更 recipe 配置、为某个来源创建调度、单次抓取、试跑一次、爬一下某个网页、下载某站公开 PDF，或验证某个来源是否能接入时，使用此工作流。

这是面向拥有完整仓库访问权限的 agent 的开发工作流。它不是运行时审批系统，也不是低代码 crawler 构建器。

## 强制触发场景

以下说法都必须视为 Harvester 来源接入或来源测试任务，不能当成普通脚本任务处理：

- “爬一下”“抓一下”“试跑一次”“单次抓取”“手动跑一次”。
- “下载这个站的 PDF”“把公开报告抓下来”“抓父目录和子目录内容”。
- “接入一个列表页、详情页、附件页、PDF、RSS、API 或混合来源”。
- “卫健委”“NHC”“国家卫生健康委”等公开网页或 PDF 目录来源。

如果执行环境有 Skill 工具，必须先加载本 skill。没有 Skill 工具时，必须先阅读本文件，再做任何抓取、脚本、代码或配置操作。

## 禁止绕过 Harvester

Harvester 的目标是控制平面，不是一次性下载脚本集合。Agent 不得把以下做法作为交付方案：

- 新建 `download_*.py`、`scrape_*.py`、`crawl_*.py` 等独立下载器来替代 source、recipe、crawl run、raw_object 和 extractor pipeline。
- 直接把网页、PDF 或解析结果写入 `downloads/`、`*_pdfs/`、临时 JSON/CSV 目录作为最终成果。
- 绕过 Harvester API/CLI 直接修改生产数据库状态。
- 因为用户没有要求定时任务，就声称“项目没有适配单次抓取功能”，然后改写为仓库外脚本。

允许写临时探测脚本或命令来理解页面结构，但必须同时满足：

- 只用于分析页面结构、反爬行为、链接模式或样例 payload。
- 不能作为最终交付路径。
- 探测结论必须转化为 recipe、executor、extractor、fixture、测试或预览报告。
- 任务结束前报告是否留下了临时文件，并询问用户是否清理。

如果发现仓库里已有绕过 Harvester 的临时下载脚本，先停止沿用该脚本；除非用户明确要求清理，否则不要删除它，而是说明它应迁移到 Harvester pipeline。

## 单次抓取与调度

单次抓取是正式运行模式，不等于 schedule。

当用户只要求“爬一下”“试跑一次”“抓这批 PDF”时：

1. 不要创建 active schedule。
2. 仍然使用 Harvester source、recipe、crawl run、raw_object、extract job、content_item、item_version 和 chunk。
3. 优先使用现有 API/CLI：
   - `uv run harvester crawl run --source-id <id> --recipe-id <id>`
   - `uv run harvester worker once --job-type extract --limit <n>`
   - 对 discovery 产生的详情页或 PDF target，继续按需运行 `uv run harvester worker once --job-type crawl --limit <n>` 和 `uv run harvester worker once --job-type extract --limit <n>`，直到本次目标队列处理完成。
4. 如果需要 embedding，再运行 `uv run harvester worker once --job-type embed_chunks --limit <n>`。
5. 输出单次抓取报告，不输出长期 schedule 已启用的结论。

当前 `/crawl/run` 和 `uv run harvester crawl run` 要求 source 已是 `watched` 或 `active`，recipe 已是 `approved`。如果 source/recipe 还未达到这些状态：

- 没有用户明确批准前，只能做 fixture、extractor、配置和 dry-run 风格验证。
- 如果用户明确要求运行一次真实抓取，可以请求一次性运行所需的 promote/approve；这仍然不代表允许创建 active schedule。
- 不得把“需要批准 source/recipe”误解为“只能做定时抓取”。

## 卫健委/NHC 场景要求

卫健委这类父目录到子目录/详情页/PDF 的来源，必须按多级 discovery 处理：

- 父目录或列表页 raw_object 只表示本次看到的目录页。
- 子目录、分页、详情页和 PDF 附件必须成为受 recipe discovery scope 限制的 crawl target。
- 详情页和 PDF 都要保留 raw evidence；PDF 文本通过 PDF extractor 进入 content item / item_version / chunk。
- 不能只把 PDF 下载到本地目录；本地文件只能是 Harvester archive 的实现细节。
- 预览报告必须列出父目录 URL、发现的子目录/详情页/PDF 数量、样例标题、样例 PDF URL、content item 数量和未覆盖的目录层级。

## 文件资产归档约定

抓取到的 PDF、图片、附件或其他二进制文件，必须按 raw evidence 处理：

- 统一写入 Harvester archive，由 `HARVESTER_ARCHIVE_PATH` 控制根目录；不要由来源代码自定义 `nhc_pdfs/`、`downloads/` 等目录。
- PDF、图片、Word、Excel、ZIP 等资产必须保留原文件格式和扩展名，例如 `.pdf`、`.png`、`.docx`；不得统一保存成 `.raw`。
- 资产类文件必须放入类型化目录，例如 `assets/pdf/`、`assets/images/`、`assets/files/`；网页和 API payload 可放入 `pages/` 类目录。
- 文件名默认使用来源 URL 或响应头中的原始文件名，清理非法路径字符即可；只有发生文件名冲突时，才追加短的 crawl/run 后缀。不得一开始就重命名成纯 UUID、hash 或不可读字符串。
- 数据库通过 `raw_objects.storage_uri`、`content_type`、`content_hash`、`byte_size`、`retain_until` 追踪文件；标题、原始 URL、canonical URL、文件类型、hash、所属 source/target/content item 必须放在数据库 metadata 和抽取结果里。
- 原始文件默认是短保留 evidence cache。长期可搜索内容必须来自 extractor 生成的 `content_item`、`item_version` 和 `chunk`。
- PDF 已有 binary fetch 和 `PdfTextExtractor` 路径，应优先复用。
- 图片、Word、Excel、ZIP、音视频或其他附件目前不能假定已经完整支持。需要新增时，必须先扩展 `CrawlTarget.media_type`、content type allowlist、binary fetch 规则、extractor/metadata 处理和测试。
- 如果只是为了人工检查而导出一份可读文件，必须标记为临时调试输出；不能作为 Harvester 的正式存储位置。

## 必读上下文

修改前，阅读以下文件或相关章节：

- `harvester/api/routers/recipes.py`
- `harvester/extractors/registry.py`
- `harvester/extractors/` 中的现有示例
- `tests/extractors/`、`tests/jobs/` 和 `tests/integration/` 中的现有测试

如果涉及前端 UI，还必须阅读 `DESIGN.md`，并参考仓库中可用的 Animal Island UI 文档，例如 `.agent/skills/animal-island-ui.md`；如果后续存在 `AI_USAGE.md`，也必须读取。

## 复用优先规则

除非存在明确不匹配，否则必须复用现有能力。

添加新的来源专用代码前，先搜索现有代码：

- `harvester/extractors/`
- `harvester/jobs/`
- `harvester/api/routers/recipes.py`
- `tests/extractors/`
- `tests/jobs/`
- `tests/integration/`
- README 中 CDC、Sina 和 PDF discovery 的示例

按以下顺序选择最小且匹配的变更：

1. 添加或调整 `recipe.config`。
2. 复用现有 executor：`firecrawl`、`http_fetch`、`rss_parse` 或 `static`。
3. 复用现有 extractor 或 registry 模式。
4. 扩展 selector、URL pattern、discovery option 或 content type handling 的配置。
5. 只有当来源语义无法适配现有 extractor 时，才新增 extractor。

新增 extractor 时，仍然必须复用现有 registry、pipeline、chunking、deduplication 和 fixture 测试模式。

## 工作流

按顺序执行以下步骤：

1. 识别来源：入口 URL、内容类型、期望的 content item 粒度，以及它是列表页、详情页、PDF、API、RSS feed 还是混合来源。
2. 识别运行模式：preview/dry-run、单次抓取、还是长期 schedule。用户没有明确要求长期抓取时，默认按单次或 preview 处理。
3. 执行复用优先搜索，并记录结果。
4. 选择接入方式：仅配置、扩展现有 extractor，或新增 extractor。
5. 当代码行为发生变化时，先添加或更新测试，再实现。
6. 实现能让测试通过的最小变更。
7. 提议启用前，运行 preview、dry-run 或用户批准的单次抓取/抽取流程。
8. 生成预览或单次抓取报告。
9. 以草案形式提出 source、recipe 和 schedule 启用方案；如果用户只要单次抓取，schedule 必须写为“不创建”。
10. 在用户明确批准启用前，不得 promote source、approve recipe、创建 active schedule，或运行正式长期抓取。

## 预览报告

每个来源接入任务都必须按以下格式生成简明报告：

```text
来源：
入口 URL：
运行模式：preview / 单次抓取 / 长期 schedule 草案
接入方式：
复用判断：
- 复用 executor：是/否，原因
- 复用 extractor：是/否，原因
- 新增代码范围：
- 没有复用的理由：
抓取结果：
发现 targets：
- 详情页：
- PDF：
- 其他文件/图片：
抽取 content items：
样例标题：
原文链接样例：
PDF 链接样例：
其他文件链接样例：
去重情况：
归档位置：HARVESTER_ARCHIVE_PATH / raw_objects.storage_uri；PDF 等资产应保留原扩展名和可读文件名，不得是来源自定义下载目录
建议调度：不创建 / 每 N 秒或 cron 草案
限制/待确认：
启用草案：
```

报告必须让用户能够判断抽取内容是否正确。优先提供样例标题、canonical URL 和 item 数量，而不是底层日志。

## 启用边界

在用户明确批准前，agent 可以：

- 修改代码。
- 添加或更新 fixture。
- 添加或更新测试。
- 运行 preview 或 dry-run 命令。
- 报告启用草案。
- 在用户已明确批准“真实单次抓取”时，通过 Harvester API/CLI 做一次性 crawl/extract，并报告结果。

在用户明确批准前，agent 不得：

- 将 source promote 为 `watched`。
- approve recipe。
- 创建 active long-running schedule。
- 触发正式长期抓取。
- 把单次抓取请求升级为长期 schedule。

如果用户明确要求 approve 或 enable 某个来源，必须通过 Harvester API 或 CLI 执行状态变更。不要直接写生产数据库状态。

## 测试期望

优先进行聚焦验证：

- extractor 变更：运行对应的 `uv run pytest tests/extractors/... -q` 命令。
- discovery 或 job 行为变更：运行对应的 `uv run pytest tests/jobs/... -q` 命令。
- CLI 或 API 工作流变更：运行覆盖该路径的窄范围测试。
- live smoke test 必须要求显式环境变量，不能成为默认 CI 要求。

准确报告哪些命令通过或失败。
