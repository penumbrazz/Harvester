---
name: harvester-source-onboarding
description: Use when adding or changing Harvester crawler sources, recipes, schedules, extractors, discovery rules, fixtures, or source-specific crawl behavior. Guides agents through reuse-first implementation, preview reporting, and user-approved activation.
---

# Harvester Source Onboarding

## Purpose

Use this workflow whenever a user asks to add a new crawl source, add a new URL to harvest, modify a source-specific extractor, change recipe configuration, or create a schedule for a source.

This is a development workflow for agents with full repository access. It is not a runtime approval system and it is not a low-code crawler builder.

## Required Context

Before making changes, read these files or the relevant sections:

- `AGENTS.md`
- `README.md`
- `docs/superpowers/specs/2026-05-18-harvester-source-onboarding-design.md`
- `harvester/api/routers/recipes.py`
- `harvester/extractors/registry.py`
- Existing examples in `harvester/extractors/`
- Existing tests in `tests/extractors/`, `tests/jobs/`, and `tests/integration/`

If frontend UI is involved, also read `DESIGN.md` and `AI_USAGE.md`.

## Reuse-First Rule

Reuse is mandatory unless there is a clear mismatch.

Search existing code before adding new source-specific code:

- `harvester/extractors/`
- `harvester/jobs/`
- `harvester/api/routers/recipes.py`
- `tests/extractors/`
- `tests/jobs/`
- `tests/integration/`
- README examples for CDC, Sina, and PDF discovery

Choose the smallest fitting change in this order:

1. Add or adjust `recipe.config`.
2. Reuse an existing executor: `firecrawl`, `http_fetch`, `rss_parse`, or `static`.
3. Reuse an existing extractor or registry pattern.
4. Extend configuration for selectors, URL patterns, discovery options, or content type handling.
5. Add a new extractor only when the source semantics do not fit the existing extractors.

When adding a new extractor, still reuse the existing registry, pipeline, chunking, deduplication, and fixture test patterns.

## Workflow

Follow these steps in order:

1. Identify the source: entry URL, content type, desired content item granularity, and whether it is a list page, detail page, PDF, API, RSS feed, or mixed source.
2. Perform the reuse-first search and record the result.
3. Pick the integration approach: config-only, existing extractor extension, or new extractor.
4. Add or update tests before implementation when code behavior changes.
5. Implement the smallest change that makes the tests pass.
6. Run a preview or dry-run crawl/extraction flow before proposing activation.
7. Produce the preview report.
8. Propose source, recipe, and schedule activation as a draft.
9. Wait for the user to explicitly approve activation before promoting sources, approving recipes, creating active schedules, or running formal long-lived crawls.

## Preview Report

Every onboarding task must produce a concise report in this format:

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

The report must let the user judge whether the extracted content is correct. Prefer sample titles, canonical URLs, and item counts over low-level logs.

## Activation Boundary

Before explicit user approval, agents may:

- Change code.
- Add or update fixtures.
- Add or update tests.
- Run preview or dry-run commands.
- Report activation drafts.

Before explicit user approval, agents must not:

- Promote a source to `watched`.
- Approve a recipe.
- Create an active long-running schedule.
- Trigger formal long-lived crawling.

If the user explicitly says to approve or enable the source, use Harvester API or CLI for state changes. Do not write production database state directly.

## Testing Expectations

Prefer focused verification:

- For extractor changes, run the relevant `uv run pytest tests/extractors/... -q` command.
- For discovery or job behavior, run the relevant `uv run pytest tests/jobs/... -q` command.
- For CLI or API workflow changes, run the narrow test covering that path.
- Live smoke tests must require an explicit environment variable and should not become default CI requirements.

Report exactly which commands passed or failed.
