---
name: harvester-source-onboarding
description: 添加或修改 Harvester 抓取源、recipe、调度、extractor、发现规则、fixture 或特定来源抓取行为时使用。指导 agent 采用复用优先实现、预览报告和用户批准后启用流程。
---

# Harvester 来源接入

## 目的

当用户要求添加新的抓取来源、添加新的采集 URL、修改来源专用 extractor、变更 recipe 配置，或为某个来源创建调度时，使用此工作流。

这是面向拥有完整仓库访问权限的 agent 的开发工作流。它不是运行时审批系统，也不是低代码 crawler 构建器。

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
2. 执行复用优先搜索，并记录结果。
3. 选择接入方式：仅配置、扩展现有 extractor，或新增 extractor。
4. 当代码行为发生变化时，先添加或更新测试，再实现。
5. 实现能让测试通过的最小变更。
6. 提议启用前，运行 preview 或 dry-run 抓取/抽取流程。
7. 生成预览报告。
8. 以草案形式提出 source、recipe 和 schedule 启用方案。
9. 在用户明确批准启用前，不得 promote source、approve recipe、创建 active schedule，或运行正式长期抓取。

## 预览报告

每个来源接入任务都必须按以下格式生成简明报告：

```text
来源：
入口 URL：
接入方式：
复用判断：
- 复用 executor：是/否，原因
- 复用 extractor：是/否，原因
- 新增代码范围：
- 没有复用的理由：
抓取结果：
发现 targets：
抽取 content items：
样例标题：
原文链接样例：
去重情况：
建议调度：
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

在用户明确批准前，agent 不得：

- 将 source promote 为 `watched`。
- approve recipe。
- 创建 active long-running schedule。
- 触发正式长期抓取。

如果用户明确要求 approve 或 enable 某个来源，必须通过 Harvester API 或 CLI 执行状态变更。不要直接写生产数据库状态。

## 测试期望

优先进行聚焦验证：

- extractor 变更：运行对应的 `uv run pytest tests/extractors/... -q` 命令。
- discovery 或 job 行为变更：运行对应的 `uv run pytest tests/jobs/... -q` 命令。
- CLI 或 API 工作流变更：运行覆盖该路径的窄范围测试。
- live smoke test 必须要求显式环境变量，不能成为默认 CI 要求。

准确报告哪些命令通过或失败。
