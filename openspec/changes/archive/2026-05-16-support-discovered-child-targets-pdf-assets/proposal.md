## Why

Harvester 目前的公开抓取以 `source.url` 为单个固定页面入口，但许多真实信息源只在固定父页面上发布动态子页面，完整内容又进一步放在 PDF 附件中。以中国疾控中心流感周报为例，固定列表页每周更新详情页 URL，而最完整的周报正文在详情页链接的 PDF 中；如果只抓固定页面，会丢失核心资料内容。

## What Changes

- 新增受控的 discovered crawl target 能力：从固定 Source 入口页发现详情页和资产 URL，持久化 target 状态，并通过现有 job/worker 机制抓取。
- 新增 target 层的父子关系、角色、深度、幂等键和审计元数据，避免把动态子页面膨胀成 Source。
- 扩展 recipe config 表达发现规则、允许域名/path/content-type、最大深度、每轮 target 上限和内容优先级。
- 新增详情页到 PDF asset 的发现流程，支持列表页、详情页、PDF 三阶段 raw evidence 链路。
- 新增 PDF asset extraction 能力：将 PDF raw payload 抽取为文本，并只从 `item_version -> chunk` 开始进入搜索和 embedding。
- 保持 public-web fetch policy、raw payload archive、audit、retention、job idempotency 和 frontier/dedup 边界。

## Capabilities

### New Capabilities

- `discovered-crawl-targets`: 固定 Source 入口页发现动态子页面或资产 URL，并以受控 target 队列完成抓取、去重、审计和下游抽取。
- `pdf-asset-extraction`: 将公开 PDF 附件作为 raw evidence 保存，并抽取 PDF 文本生成资料库 item version、chunk 和 embedding job。

### Modified Capabilities

- 无。

## Impact

- 数据库：新增 discovered crawl target 持久化表或等价 target 状态模型，关联 source、raw object、job 和父子 target。
- 后端 pipeline：扩展 crawl job payload/handler、extraction service、extractor registry、recipe config 校验和 frontier 更新逻辑。
- 抽取器：新增 CDC 周报列表/详情发现器和 PDF 文本抽取器，保留 fixture-first 测试路径。
- API/CLI/前端：管理界面可继续通过 Source/Recipe/Schedule 操作固定入口；运维视图需要能观察 target/job 状态但不得暴露 raw payload。
- 安全：所有发现出的 URL 必须重新经过 fetch policy、scope allowlist 和 content-type 限制，不能开放通用递归抓取。
