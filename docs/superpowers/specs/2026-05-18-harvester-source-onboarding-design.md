# Harvester Source Onboarding 设计

## 背景

Harvester 现在已经有 Source、Recipe、Schedule、Crawl、Extractor、Job、Audit 和搜索闭环。新增抓取来源时，实际操作者经常是 Code Agent，而不是人手动在 UI 里配置每一步。

当前问题不是缺少一个复杂的低代码爬虫平台，而是缺少一套仓库内的 Agent 操作规范：Agent 需要知道如何判断是否复用现有实现、如何添加 fixture 和测试、如何预览抓取效果，以及什么时候可以创建启用草案。

## 目标

新增一个跨 Agent 可读的项目级 onboarding 工作流，让拿到完整仓库上下文的 Code Agent 能稳定完成新抓取来源接入。

工作流覆盖：

- 理解新来源的入口 URL、内容类型和采集粒度。
- 优先复用现有 recipe、executor、extractor、pipeline 和测试结构。
- 在需要时新增或扩展 extractor。
- 添加 fixture 测试或 live smoke 测试。
- 输出一次 preview/dry-run 抓取效果报告。
- 生成 source、recipe、schedule 的启用草案。
- 等用户明确批准后，才执行正式启用动作。

## 非目标

本设计不新增产品级权限系统，也不扩展安全策略。

明确不做：

- 不新增 allowlist 机制。
- 不设计复杂审批流。
- 不新增 sandbox、登录态 profile 或高风险 recipe 管控。
- 不把 Harvester 改造成低代码爬虫配置平台。

现有 fetch policy 保持不变。这里的“批准”是 Agent 工作流门槛，不是新的 runtime 权限模型。

## 文件结构

主规范放在中立目录：

```text
.agent/skills/harvester-source-onboarding/SKILL.md
```

Agent 专属入口只做转发，避免多份规则漂移：

```text
.codex/skills/harvester-source-onboarding/SKILL.md
.claude/skills/harvester-source-onboarding/SKILL.md
```

`.codex` 和 `.claude` 下的文件只说明 canonical workflow 在 `.agent/skills/harvester-source-onboarding/SKILL.md`。

项目根目录 `AGENTS.md` 后续应增加一条约束：新增或修改抓取来源、extractor、recipe、schedule 时，必须先阅读并遵循 `.agent/skills/harvester-source-onboarding/SKILL.md`。

## Agent 工作流

新增抓取来源时，Agent 必须按固定顺序执行：

1. 理解目标来源：入口 URL、内容类型、预期采集粒度、是否为列表页、详情页、PDF、API 或 RSS。
2. 复用优先检查：搜索现有 recipe、executor、extractor、测试 fixture 和 pipeline 模式。
3. 选择接入方式：只新增配置、扩展现有 extractor，或新增 extractor。
4. 写或更新测试：优先 fixture 测试；需要真实网络验证时添加 live smoke，但 live smoke 不作为默认 CI 必跑项。
5. 跑 preview/dry-run：展示一次抓取和抽取效果。
6. 输出 preview 报告。
7. 生成 source、recipe、schedule 启用草案。
8. 等用户明确说“批准启用”后，才执行 promote、approve、create active schedule 或正式 crawl。

没有 preview 报告时，Agent 不应启用长期 schedule，也不应把 source 推进到 watched。

## 复用优先规则

复用优先是硬规则。Agent 在新增代码前必须搜索并说明是否可以复用：

- `harvester/extractors/`
- `harvester/jobs/`
- `harvester/api/routers/recipes.py`
- `tests/extractors/`
- `tests/jobs/`
- `tests/integration/`
- README 中已有的 CDC、Sina、PDF discovery 示例

判断顺序：

1. 先看是否只需要新增或调整 `recipe.config`。
2. 再看是否能复用现有 executor：`firecrawl`、`http_fetch`、`rss_parse`、`static`。
3. 再看是否能复用现有 extractor：CDC、Sina、PDF text、fixture extractor 或 registry 模式。
4. 如果只是 selector、URL pattern、discovery config 不同，优先扩展配置，不新增类。
5. 只有当现有 extractor 的抽取语义明显不匹配时，才新增 extractor。
6. 新增 extractor 时，也必须复用 registry、chunking、dedup、pipeline 和测试 fixture 结构。

## Preview 报告

Preview 报告保持短，但必须足够判断“抓得对不对”。

报告格式：

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

启用草案应列出拟创建或更新的 source、recipe 和 schedule，但不自动执行长期启用动作。

## 启用边界

Agent 可以在用户批准前完成：

- 代码实现。
- fixture 或测试更新。
- preview/dry-run。
- preview 报告。
- source、recipe、schedule 的启用建议。

Agent 在用户明确批准前不能完成：

- promote source 到 `watched`。
- approve recipe 到 `approved`。
- 创建 active schedule。
- 触发正式长期抓取。

如果用户明确说“批准启用”，Agent 可以继续通过 Harvester API 或 CLI 执行启用动作。CLI 的状态变更仍必须通过 HTTP API，不直接创建数据库 session。

## 测试策略

新增来源默认测试顺序：

1. 优先添加 fixture 测试，验证 extractor 解析和内容项输出。
2. 如果来源需要 discovery，添加 target 发现相关测试。
3. 如果涉及 pipeline 行为，添加 jobs 层测试。
4. 真实网络测试只作为 live smoke，必须通过环境变量显式启用。
5. 完成前运行相关测试，并在最终报告里说明执行结果。

测试应遵循现有项目原则：AAA 模式、隔离外部服务、保持最小 diff。

## 后续实现步骤

下一步实现应创建：

- `.agent/skills/harvester-source-onboarding/SKILL.md`
- `.codex/skills/harvester-source-onboarding/SKILL.md`
- `.claude/skills/harvester-source-onboarding/SKILL.md`

并在 `AGENTS.md` 中加入对应约束。实现不需要新增 API、数据库迁移或前端页面。
