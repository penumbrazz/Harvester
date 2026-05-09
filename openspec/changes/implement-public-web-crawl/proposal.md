## Why

Harvester 已经具备 schema、状态机、job/frontier、fixture 抽取、去重和搜索，但抓取仍停留在 stub/fixture 层。下一步必须打通真实公开网页抓取，否则系统无法验证 `raw_object -> content_item -> item_version -> chunk -> search` 的生产闭环。

同时 Harvester 会运行在 home lab 内网，并允许 agent 通过 API/CLI 触发抓取。真实抓取必须自带最小 fetch policy，防止误抓 localhost、private IP、link-local、NAS、路由器或 Firecrawl 管理口。

## What Changes

- Add a real public web crawl path backed by Firecrawl-compatible HTTP API calls.
- Add a minimal fetch policy for public `http`/`https` targets, including DNS/IP classification, redirect target validation, timeout and size limits.
- Add archive storage for raw public payloads so Postgres keeps metadata/hash/storage URI, not inline payloads.
- Add API and CLI entry points for running a crawl against an approved source/recipe.
- Persist crawl run status, raw object metadata, audit events and failure reasons.
- Connect the crawl output to existing fixture extractors for CDC-style public pages, proving the raw-to-search chain.
- Add CDC live/smoke coverage that can be run explicitly without making regression tests depend on network availability.

## Capabilities

### New Capabilities
- `public-web-crawl`: Public web crawl execution, fetch policy enforcement, raw payload archival, API/CLI crawl triggering and CDC crawl smoke behavior.

### Modified Capabilities

## Impact

- Adds a production Firecrawl adapter next to the existing stub adapter.
- Adds fetch policy/domain validation code used by API and adapter/job execution.
- Extends API routers and CLI commands with crawl execution endpoints.
- Adds archive filesystem configuration and raw payload write path.
- Adds tests for safety policy, adapter behavior, API/CLI contracts, raw object metadata, audit failure records and CDC crawl smoke.
- Does not add login-state crawling, custom scripts, browser profiles, social media recipes, LightRAG or MCP adapter behavior.
