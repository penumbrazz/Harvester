# TODOS

## Harvester

### 二期接入 LightRAG、轻量 KG 和 MCP 适配层

**What:** 在 MVP 搜索闭环稳定后，分三步接入 LightRAG batch index、轻量 KG 和可选 MCP adapter。

**Why:** Harvester 的长期目标是为 Topic Watch 提供可追溯 KG/RAG 能力，但 MVP 已收敛到抓取、抽取、去重、搜索和审计闭环。把二期能力显式记录，避免它们污染第一版范围，也避免后续丢失方向。

**Context:** Harvester 的事实源必须继续是 Postgres 中的 raw/content/version/chunk/audit 数据。LightRAG 只能作为从 `content_item`、`item_version`、`chunk` 重建出来的派生索引，不能成为事实源。MCP 只做工具入口，Agent Skill 仍是主操作规范。

**Effort:** L
**Priority:** P1
**Depends on:** MVP 的 `content_item`、`item_version`、`chunk`、关键词搜索、向量搜索稳定；embedding model 和向量维度固定。

### 补完整 fetch policy

**What:** 补全 fetch policy 的 allowlist/approval 机制。当前已实现 DNS/IP 过滤、重定向检查、超时和请求大小限制（`harvester/domain/fetch_policy.py`），但缺少 allowlist/approval 策略。

**Why:** 当前 fetch policy 可支撑个人手动使用，但 agent 自动 propose source 前必须补 allowlist 机制，否则容易误抓内网管理口、NAS、路由器或 Firecrawl 管理 API。

**Context:** Harvester 运行在 home lab 内网，API/CLI 会允许上层 agent 触发抓取。fetch policy 应该在 API 层和 adapter 层同时生效，拒绝原因写入 `audit_events`，方便诊断和回放。

**Effort:** M
**Priority:** P2
**Depends on:** API token、audit_events、source/recipe 状态机。

### 设计登录态和高风险 recipe 的 auth profile / sandbox

**What:** 为需要登录态、浏览器 profile、视觉模型或自定义脚本的 recipe 设计 auth profile、人工审批、密钥存储、审计和沙箱边界。

**Why:** 微博、X、小红书和登录站点不能让 agent 任意执行脚本或保存明文 cookie。这个能力风险高，应在公开网页 MVP 稳定后单独设计。

**Context:** 当前 recipe 模型预留了 `browser_profile`、`screenshot_vlm`、`custom_script` 等 executor 类型，但第一版不应开放生产使用。后续支持登录态站点前，需要先明确 token/cookie 存储、profile 生命周期、审批状态和执行隔离。

**Effort:** L
**Priority:** P2
**Depends on:** fetch policy、recipe 状态机、audit_events。

## Completed
