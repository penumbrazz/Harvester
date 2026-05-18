# Harvester Source Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cross-agent Harvester source onboarding skill that guides agents through reuse-first crawler source additions, preview reporting, and user-approved activation.

**Architecture:** The canonical workflow lives under `.agent/skills/harvester-source-onboarding/SKILL.md` so multiple agents can read the same source of truth. Codex and Claude each get a thin forwarding skill that points to the canonical workflow. `AGENTS.md` gets one project-level rule requiring agents to use the canonical workflow before changing crawler sources, extractors, recipes, or schedules.

**Tech Stack:** Markdown skill files, repository agent conventions, existing Harvester project docs.

---

## File Structure

- Create `.agent/skills/harvester-source-onboarding/SKILL.md`: canonical source onboarding skill with reuse-first workflow, preview report format, activation boundary, and verification checklist.
- Create `.codex/skills/harvester-source-onboarding/SKILL.md`: Codex-facing forwarding skill that instructs Codex to read the canonical `.agent` workflow.
- Create `.claude/skills/harvester-source-onboarding/SKILL.md`: Claude-facing forwarding skill that instructs Claude to read the canonical `.agent` workflow.
- Modify `AGENTS.md`: add a concise rule requiring the source onboarding workflow for crawler source, extractor, recipe, or schedule changes. Preserve existing uncommitted edits in this file.

## Implementation Tasks

### Task 1: Create Canonical Cross-Agent Skill

**Files:**
- Create: `.agent/skills/harvester-source-onboarding/SKILL.md`

- [ ] **Step 1: Create the canonical skill file**

Use `apply_patch` to create `.agent/skills/harvester-source-onboarding/SKILL.md` with this content:

````markdown
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
````

- [ ] **Step 2: Review the canonical skill text**

Run:

```bash
sed -n '1,260p' .agent/skills/harvester-source-onboarding/SKILL.md
```

Expected: The file contains the metadata header, reuse-first rule, workflow, preview report, activation boundary, and testing expectations.

- [ ] **Step 3: Commit the canonical skill**

Run:

```bash
git add .agent/skills/harvester-source-onboarding/SKILL.md
git commit -m "docs: add harvester source onboarding skill"
```

Expected: Git creates a commit containing only the canonical skill file.

### Task 2: Add Agent-Specific Forwarding Skills

**Files:**
- Create: `.codex/skills/harvester-source-onboarding/SKILL.md`
- Create: `.claude/skills/harvester-source-onboarding/SKILL.md`

- [ ] **Step 1: Create the Codex forwarding skill**

Use `apply_patch` to create `.codex/skills/harvester-source-onboarding/SKILL.md` with this content:

````markdown
---
name: harvester-source-onboarding
description: Use when adding or changing Harvester crawler sources, recipes, schedules, extractors, discovery rules, fixtures, or source-specific crawl behavior.
---

# Harvester Source Onboarding

Read and follow the canonical cross-agent workflow at:

```text
.agent/skills/harvester-source-onboarding/SKILL.md
```

Do not duplicate or reinterpret the workflow in this file. The `.agent` skill is the source of truth.
````

- [ ] **Step 2: Create the Claude forwarding skill**

Use `apply_patch` to create `.claude/skills/harvester-source-onboarding/SKILL.md` with this content:

````markdown
---
name: harvester-source-onboarding
description: Use when adding or changing Harvester crawler sources, recipes, schedules, extractors, discovery rules, fixtures, or source-specific crawl behavior.
---

# Harvester Source Onboarding

Read and follow the canonical cross-agent workflow at:

```text
.agent/skills/harvester-source-onboarding/SKILL.md
```

Do not duplicate or reinterpret the workflow in this file. The `.agent` skill is the source of truth.
````

- [ ] **Step 3: Verify forwarding files point to the canonical workflow**

Run:

```bash
rg -n "canonical cross-agent workflow|\\.agent/skills/harvester-source-onboarding/SKILL.md" .codex/skills/harvester-source-onboarding .claude/skills/harvester-source-onboarding
```

Expected: Both forwarding skill files contain the canonical `.agent` path.

- [ ] **Step 4: Commit forwarding skills**

Run:

```bash
git add .codex/skills/harvester-source-onboarding/SKILL.md .claude/skills/harvester-source-onboarding/SKILL.md
git commit -m "docs: add source onboarding skill forwarders"
```

Expected: Git creates a commit containing only the two forwarding skill files.

### Task 3: Add Project-Level Rule to AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Inspect existing AGENTS.md edits before modifying**

Run:

```bash
git diff -- AGENTS.md
```

Expected: Any existing uncommitted edits are visible. Preserve them and add only the new source onboarding rule.

- [ ] **Step 2: Add the source onboarding rule**

Use `apply_patch` to add this bullet under `## 工作方式`:

```markdown
- 新增或修改抓取来源、extractor、recipe、schedule 时，必须先阅读并遵循 `.agent/skills/harvester-source-onboarding/SKILL.md`；优先复用现有 recipe、executor、extractor、pipeline 和测试结构，能复用就复用。
```

If `## 工作方式` already has nearby skill workflow bullets, place this rule next to them.

- [ ] **Step 3: Verify the rule exists once**

Run:

```bash
rg -n "harvester-source-onboarding|能复用就复用" AGENTS.md
```

Expected: One matching project-level rule exists in `AGENTS.md`.

- [ ] **Step 4: Commit only the AGENTS.md rule when it is safe**

Run:

```bash
git diff -- AGENTS.md
git add AGENTS.md
git commit -m "docs: require source onboarding workflow"
```

Expected: The diff includes the onboarding rule and preserves any pre-existing user edits. If unrelated user edits are mixed into the same file and should not be committed, stop and ask the user how to split or handle the file.

### Task 4: Final Verification

**Files:**
- Verify: `.agent/skills/harvester-source-onboarding/SKILL.md`
- Verify: `.codex/skills/harvester-source-onboarding/SKILL.md`
- Verify: `.claude/skills/harvester-source-onboarding/SKILL.md`
- Verify: `AGENTS.md`

- [ ] **Step 1: Confirm all expected files exist**

Run:

```bash
test -f .agent/skills/harvester-source-onboarding/SKILL.md
test -f .codex/skills/harvester-source-onboarding/SKILL.md
test -f .claude/skills/harvester-source-onboarding/SKILL.md
```

Expected: All commands exit with status 0.

- [ ] **Step 2: Confirm no duplicated full workflow exists in forwarding files**

Run:

```bash
wc -l .agent/skills/harvester-source-onboarding/SKILL.md .codex/skills/harvester-source-onboarding/SKILL.md .claude/skills/harvester-source-onboarding/SKILL.md
```

Expected: The `.agent` file is substantially longer than the `.codex` and `.claude` files.

- [ ] **Step 3: Confirm the preview report and reuse rule are searchable**

Run:

```bash
rg -n "Preview Report|Reuse-First Rule|复用判断|启用草案|批准启用" .agent/skills/harvester-source-onboarding AGENTS.md docs/superpowers/specs/2026-05-18-harvester-source-onboarding-design.md
```

Expected: Matches appear in the canonical skill, design spec, and `AGENTS.md` where applicable.

- [ ] **Step 4: Check final git state**

Run:

```bash
git status --short
```

Expected: No uncommitted changes from this implementation remain. If unrelated pre-existing changes remain, report them explicitly.
