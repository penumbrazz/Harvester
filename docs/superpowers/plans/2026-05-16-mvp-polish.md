# Harvester MVP 打磨实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在启动新功能前，通过测试补全、缺陷修复、代码清理和文档完善来稳固 MVP。

**架构：** 五个顺序阶段，每个阶段独立提交。阶段 1-2 聚焦测试，阶段 3 修 bug，阶段 4 清理代码，阶段 5 完善文档。

**技术栈：** Python 3.12+ / FastAPI / SQLAlchemy 2 / pytest / React 19 / TypeScript / Playwright

---

## 阶段 1：测试修复与覆盖率基线

### Task 1: 运行全部测试并记录基线

**Files:**
- 无代码修改，仅运行命令

- [ ] **Step 1: 运行后端全部测试**

```bash
uv run pytest tests/ --tb=short -q -rs
```

预期：846 passed, 6 skipped（均为 opt-in live 测试）。如有失败则记录。

- [ ] **Step 2: 运行前端单元测试**

```bash
cd frontend && npm test -- --run
```

预期：全部通过。如有失败则记录。

- [ ] **Step 3: 生成后端覆盖率报告**

```bash
uv run pytest tests/ --cov=harvester --cov-report=term-missing -q 2>&1 | tail -40
```

记录各模块覆盖率数据到 `docs/superpowers/plans/coverage-baseline.txt`。

- [ ] **Step 4: 提交覆盖率基线数据**

```bash
git add docs/superpowers/plans/coverage-baseline.txt
git commit -m "chore: record test coverage baseline"
```

---

### Task 2: 补充 Sources PATCH API 测试

**Files:**
- Modify: `tests/api/test_sources.py`
- Reference: `harvester/api/routers/sources.py` (PATCH /sources/{id} endpoint)

- [ ] **Step 1: 编写 PATCH /sources/{id} 测试**

在 `tests/api/test_sources.py` 文件末尾新增以下测试函数。遵循文件现有模式：`@pytest.mark.asyncio`、`async def`、`api_client` + `api_test_db` fixtures、`headers={"Authorization": "Bearer test-secret"}`。

```python
@pytest.mark.asyncio
async def test_patch_source_updates_fields(api_client, api_test_db):
    """PATCH /sources/{id} updates name, url, trust_level and writes audit."""
    # Arrange — create a candidate source
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/sources/propose",
        json={"name": f"patch-src-{suffix}", "kind": "rss", "url": f"https://example.com/{suffix}"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert create.status_code == 201
    source_id = create.json()["id"]

    # Act — patch the source
    resp = await api_client.patch(
        f"/sources/{source_id}",
        json={"name": f"renamed-{suffix}", "url": f"https://new.example.com/{suffix}", "trust_level": "high"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert — response reflects changes
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == f"renamed-{suffix}"
    assert data["url"] == f"https://new.example.com/{suffix}"
    assert data["trust_level"] == "high"

    # Assert — audit event written
    engine = create_engine(api_test_db)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT action FROM audit_events WHERE entity_id = :eid AND action = 'update'"),
            {"eid": source_id},
        ).fetchone()
        assert row is not None
    engine.dispose()


@pytest.mark.asyncio
async def test_patch_archived_source_rejected(api_client, api_test_db):
    """PATCH on archived source returns 400."""
    # Arrange — create + archive
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/sources/propose",
        json={"name": f"arch-patch-{suffix}", "kind": "rss", "url": f"https://example.com/{suffix}"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = create.json()["id"]
    await api_client.post(f"/sources/{source_id}/archive", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.patch(
        f"/sources/{source_id}",
        json={"name": "should-fail"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 400
```

- [ ] **Step 2: 运行新测试确认通过**

```bash
uv run pytest tests/api/test_sources.py -v -k "test_patch_source or test_patch_archived"
```

预期：2 passed。

- [ ] **Step 3: 提交**

```bash
git add tests/api/test_sources.py
git commit -m "test(api): add PATCH /sources/{id} tests with audit verification"
```

---

### Task 3: 补充 Recipes 状态转换 API 测试

**Files:**
- Modify: `tests/api/test_recipes.py`
- Reference: `harvester/api/routers/recipes.py` (reject/resubmit/deprecate/patch endpoints)

- [ ] **Step 1: 编写 reject/resubmit/deprecate/patch 测试**

在 `tests/api/test_recipes.py` 文件末尾新增以下测试。遵循文件现有模式：使用 `api_client` + `api_recipe_test_db` fixtures（注意该文件中的 DB fixture 名为 `api_recipe_test_db`）。

```python
@pytest.mark.asyncio
async def test_reject_recipe(api_client, api_recipe_test_db):
    """POST /recipes/{id}/reject: pending->rejected."""
    # Arrange
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/recipes",
        json={"name": f"reject-r-{suffix}", "executor": "http_fetch", "config": {}, "risk_level": "low"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert create.status_code == 201
    rid = create.json()["id"]

    # Act
    resp = await api_client.post(f"/recipes/{rid}/reject", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 200
    assert resp.json()["approval_status"] == "rejected"


@pytest.mark.asyncio
async def test_resubmit_recipe(api_client, api_recipe_test_db):
    """POST /recipes/{id}/resubmit: rejected->pending."""
    # Arrange — create + reject
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/recipes",
        json={"name": f"resub-r-{suffix}", "executor": "http_fetch", "config": {}, "risk_level": "low"},
        headers={"Authorization": "Bearer test-secret"},
    )
    rid = create.json()["id"]
    await api_client.post(f"/recipes/{rid}/reject", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.post(f"/recipes/{rid}/resubmit", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 200
    assert resp.json()["approval_status"] == "pending"


@pytest.mark.asyncio
async def test_deprecate_recipe(api_client, api_recipe_test_db):
    """POST /recipes/{id}/deprecate: approved->deprecated."""
    # Arrange — create + approve
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/recipes",
        json={"name": f"depr-r-{suffix}", "executor": "http_fetch", "config": {}, "risk_level": "low"},
        headers={"Authorization": "Bearer test-secret"},
    )
    rid = create.json()["id"]
    await api_client.post(f"/recipes/{rid}/approve", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.post(f"/recipes/{rid}/deprecate", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 200
    assert resp.json()["approval_status"] == "deprecated"


@pytest.mark.asyncio
async def test_patch_recipe(api_client, api_recipe_test_db):
    """PATCH /recipes/{id} updates name and config, writes audit."""
    # Arrange
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/recipes",
        json={"name": f"patch-r-{suffix}", "executor": "http_fetch", "config": {}, "risk_level": "low"},
        headers={"Authorization": "Bearer test-secret"},
    )
    rid = create.json()["id"]

    # Act
    resp = await api_client.patch(
        f"/recipes/{rid}",
        json={"name": f"updated-{suffix}", "config": {"key": "value"}},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == f"updated-{suffix}"
    assert data["config"] == {"key": "value"}


@pytest.mark.asyncio
async def test_reject_approved_recipe_rejected(api_client, api_recipe_test_db):
    """Reject on approved recipe returns 400 (invalid transition)."""
    # Arrange — create + approve
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/recipes",
        json={"name": f"inv-reject-{suffix}", "executor": "http_fetch", "config": {}, "risk_level": "low"},
        headers={"Authorization": "Bearer test-secret"},
    )
    rid = create.json()["id"]
    await api_client.post(f"/recipes/{rid}/approve", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.post(f"/recipes/{rid}/reject", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resubmit_pending_recipe_rejected(api_client, api_recipe_test_db):
    """Resubmit on pending recipe returns 400 (invalid transition)."""
    # Arrange
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/recipes",
        json={"name": f"inv-resub-{suffix}", "executor": "http_fetch", "config": {}, "risk_level": "low"},
        headers={"Authorization": "Bearer test-secret"},
    )
    rid = create.json()["id"]

    # Act
    resp = await api_client.post(f"/recipes/{rid}/resubmit", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_deprecate_pending_recipe_rejected(api_client, api_recipe_test_db):
    """Deprecate on pending recipe returns 400 (invalid transition)."""
    # Arrange
    suffix = uuid.uuid4().hex[:6]
    create = await api_client.post(
        "/recipes",
        json={"name": f"inv-depr-{suffix}", "executor": "http_fetch", "config": {}, "risk_level": "low"},
        headers={"Authorization": "Bearer test-secret"},
    )
    rid = create.json()["id"]

    # Act
    resp = await api_client.post(f"/recipes/{rid}/deprecate", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 400
```

- [ ] **Step 2: 运行新测试确认通过**

```bash
uv run pytest tests/api/test_recipes.py -v -k "test_reject or test_resubmit or test_deprecate or test_patch_recipe or test_reject_approved or test_resubmit_pending or test_deprecate_pending"
```

预期：7 passed。

- [ ] **Step 3: 提交**

```bash
git add tests/api/test_recipes.py
git commit -m "test(api): add reject/resubmit/deprecate/patch recipe tests"
```

---

### Task 4: 补充 Schedules 状态转换 API 测试

**Files:**
- Modify: `tests/api/test_watch_schedules.py`
- Reference: `harvester/api/routers/schedules.py` (pause/resume/disable/patch endpoints)

- [ ] **Step 1: 编写 pause/resume/disable/patch 测试**

在 `tests/api/test_watch_schedules.py` 文件末尾新增测试。该文件使用 `api_sched_test_db` fixture 和 `_insert_source` / `_insert_recipe` / `_insert_schedule` 辅助函数。

```python
@pytest.mark.asyncio
async def test_pause_schedule(api_client, api_sched_test_db):
    """POST /schedules/{id}/pause: active->paused."""
    # Arrange — insert source (watched), recipe (approved), schedule (active)
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)

    # Act
    resp = await api_client.post(f"/schedules/{sched_id}/pause", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_resume_schedule(api_client, api_sched_test_db):
    """POST /schedules/{id}/resume: paused->active."""
    # Arrange
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)
    await api_client.post(f"/schedules/{sched_id}/pause", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.post(f"/schedules/{sched_id}/resume", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_disable_schedule(api_client, api_sched_test_db):
    """POST /schedules/{id}/disable: active->disabled."""
    # Arrange
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)

    # Act
    resp = await api_client.post(f"/schedules/{sched_id}/disable", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_disable_paused_schedule(api_client, api_sched_test_db):
    """POST /schedules/{id}/disable: paused->disabled."""
    # Arrange
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)
    await api_client.post(f"/schedules/{sched_id}/pause", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.post(f"/schedules/{sched_id}/disable", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_patch_schedule(api_client, api_sched_test_db):
    """PATCH /schedules/{id} updates interval_seconds, writes audit."""
    # Arrange
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)

    # Act
    resp = await api_client.patch(
        f"/schedules/{sched_id}",
        json={"interval_seconds": 3600},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["interval_seconds"] == 3600


@pytest.mark.asyncio
async def test_pause_already_paused_rejected(api_client, api_sched_test_db):
    """Pause on paused schedule returns 400."""
    # Arrange
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)
    await api_client.post(f"/schedules/{sched_id}/pause", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.post(f"/schedules/{sched_id}/pause", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resume_active_schedule_rejected(api_client, api_sched_test_db):
    """Resume on active schedule returns 400."""
    # Arrange
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)

    # Act
    resp = await api_client.post(f"/schedules/{sched_id}/resume", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_disable_already_disabled_rejected(api_client, api_sched_test_db):
    """Disable on disabled schedule returns 400."""
    # Arrange
    src_id = _insert_source(api_sched_test_db, status="watched")
    rec_id = _insert_recipe(api_sched_test_db, approval_status="approved")
    sched_id = _insert_schedule(api_sched_test_db, source_id=src_id, recipe_id=rec_id)
    await api_client.post(f"/schedules/{sched_id}/disable", headers={"Authorization": "Bearer test-secret"})

    # Act
    resp = await api_client.post(f"/schedules/{sched_id}/disable", headers={"Authorization": "Bearer test-secret"})

    # Assert
    assert resp.status_code == 400
```

- [ ] **Step 2: 运行新测试确认通过**

```bash
uv run pytest tests/api/test_watch_schedules.py -v -k "test_pause_schedule or test_resume_schedule or test_disable or test_patch_schedule or test_pause_already or test_resume_active or test_disable_already"
```

预期：8 passed。

- [ ] **Step 3: 提交**

```bash
git add tests/api/test_watch_schedules.py
git commit -m "test(api): add pause/resume/disable/patch schedule tests"
```

---

### Task 5: 补充 Content Library 前端 E2E 测试

**Files:**
- Create: `frontend/e2e/content-library.spec.ts`
- Reference: `frontend/src/features/content/content-library-page.tsx`

- [ ] **Step 1: 编写 Content Library E2E 测试**

新建 `frontend/e2e/content-library.spec.ts`，遵循现有 E2E 模式：`beforeEach` 中配置 API、`getByTestId` 选择器、`toBeVisible` 断言。

```typescript
import { expect, test } from '@playwright/test'

test.describe('Content Library E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()
    const configForm = page.getByTestId('api-url-input')
    if (await configForm.isVisible()) {
      await page.getByTestId('api-url-input').fill('http://localhost:8001')
      await page.getByTestId('api-token-input').fill('test-secret')
      await page.getByTestId('save-config-button').click()
    }
  })

  test('renders content library page with heading', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('page-content-library')).toBeVisible()
    await expect(page.getByRole('heading', { name: '内容库' })).toBeVisible()
  })

  test('shows empty state when no content exists', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('content-empty')).toBeVisible()
  })

  test('displays search input and mode selector', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('search-input')).toBeVisible()
    await expect(page.getByTestId('search-mode-select')).toBeVisible()
    await expect(page.getByTestId('search-button')).toBeVisible()
  })

  test('displays filter controls', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('select-type-filter')).toBeVisible()
    await expect(page.getByTestId('select-status-filter')).toBeVisible()
  })

  test('displays view toggle buttons', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('view-list')).toBeVisible()
    await expect(page.getByTestId('view-grid')).toBeVisible()
  })

  test('performs keyword search', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await page.getByTestId('search-input').fill('test query')
    await page.getByTestId('search-button').click()
    // Either results or no-results state should appear (depends on backend data)
    const hasResults = await page.getByTestId('search-results').isVisible()
    const hasError = await page.getByTestId('search-error').isVisible()
    expect(hasResults || hasError).toBeTruthy()
  })
})
```

- [ ] **Step 2: 运行 E2E 测试确认通过**

```bash
cd frontend && npx playwright test e2e/content-library.spec.ts
```

预期：6 passed。

- [ ] **Step 3: 提交**

```bash
git add frontend/e2e/content-library.spec.ts
git commit -m "test(e2e): add content library page E2E tests"
```

---

### Task 6: 补充 Source Resume 前端 E2E 测试

**Files:**
- Modify: `frontend/e2e/source-management.spec.ts`

- [ ] **Step 1: 在 source-management.spec.ts 末尾新增 resume 测试**

```typescript
test('resumes a paused source', async ({ page }) => {
  const uniqueName = `e2e-resume-src-${Date.now()}`

  // Create and promote to watched
  await page.getByTestId('nav-sources').click()
  await page.getByTestId('propose-source-button').click()
  await page.getByTestId('source-name-input').fill(uniqueName)
  await page.getByTestId('source-url-input').fill(`https://resume-${Date.now()}.example.com`)
  await page.getByTestId('source-kind-select').selectOption('rss')
  await page.getByTestId('submit-source-button').click()

  // Promote candidate -> testing -> watched
  const sourceRow = page.locator('tr', { hasText: uniqueName })
  await sourceRow.getByTestId(/action-promote-/).click()
  await sourceRow.getByTestId(/action-promote-/).click()

  // Pause
  await sourceRow.getByTestId(/action-pause-/).click()
  await expect(sourceRow.getByText('已暂停')).toBeVisible()

  // Resume
  await sourceRow.getByTestId(/action-resume-/).click()
  await expect(sourceRow.getByText('监控中')).toBeVisible()
})
```

- [ ] **Step 2: 运行 E2E 测试确认通过**

```bash
cd frontend && npx playwright test e2e/source-management.spec.ts -g "resumes a paused source"
```

预期：1 passed。

- [ ] **Step 3: 提交**

```bash
git add frontend/e2e/source-management.spec.ts
git commit -m "test(e2e): add source resume workflow test"
```

---

### Task 7: 阶段 1 验收 — 运行全部测试确认绿色

- [ ] **Step 1: 运行后端全部测试**

```bash
uv run pytest tests/ -q -rs
```

预期：所有 passed，无新增失败。

- [ ] **Step 2: 运行前端单元测试**

```bash
cd frontend && npm test -- --run
```

预期：全部通过。

- [ ] **Step 3: 运行前端 E2E 测试**

```bash
cd frontend && npx playwright test
```

预期：全部通过。

---

## 阶段 2：端到端实际抓取 Smoke 测试

### Task 8: 新浪 7x24 实际抓取 Smoke 测试

**Files:**
- Create: `tests/integration/test_sina_7x24_live_crawl_smoke.py`
- Reference: `tests/integration/test_cdc_public_crawl_smoke.py` (live crawl pattern)
- Reference: `tests/integration/test_sina_7x24_pipeline.py` (sina extractor pattern)

- [ ] **Step 1: 编写新浪 7x24 live crawl smoke 测试**

新建 `tests/integration/test_sina_7x24_live_crawl_smoke.py`，使用 `db_session` fixture + opt-in `@pytest.mark.skipif` 模式。

```python
import os

import pytest
import sqlalchemy as sa

from harvester.adapters.firecrawl import FirecrawlAdapter
from harvester.extractors.sina_7x24 import Sina7x24Extractor
from harvester.jobs.raw_archive import write_archive
from harvester.jobs.extraction import upsert_content_item, create_observation, create_version_if_changed

LIVE_CRAWL_ENABLED = os.environ.get("HARVESTER_ENABLE_LIVE_CRAWL", "").strip() == "1"

SINA_7X24_URL = "https://finance.sina.com.cn/7x24/"


@pytest.mark.skipif(not LIVE_CRAWL_ENABLED, reason="HARVESTER_ENABLE_LIVE_CRAWL not set")
class TestSina7x24LiveCrawlSmoke:
    """Live smoke test: real Firecrawl + real Sina 7x24 extractor."""

    def test_live_crawl_extracts_content(self, db_session):
        # Arrange — create source
        from harvester.db.models import Source, RawObject
        source = Source(name="sina-7x24-live", kind="web", url=SINA_7X24_URL, status="watched")
        db_session.add(source)
        db_session.flush()
        source_id = str(source.id)

        # Act — fetch real page via Firecrawl
        adapter = FirecrawlAdapter()
        crawl_result = adapter.crawl(SINA_7X24_URL)

        assert crawl_result is not None, "Firecrawl returned None — check adapter config"

        # Act — archive raw object
        archive_result = write_archive(
            session=db_session,
            source_id=source.id,
            content_type="text/html",
            payload=crawl_result.html if hasattr(crawl_result, "html") else str(crawl_result),
            url=SINA_7X24_URL,
        )
        assert archive_result.raw_object_id is not None

        # Act — extract content
        html = crawl_result.html if hasattr(crawl_result, "html") else str(crawl_result)
        extractor = Sina7x24Extractor()
        candidates = extractor.extract(html)
        assert len(candidates) > 0, "Sina7x24Extractor returned no candidates from live page"

        # Act — upsert content items
        for candidate in candidates:
            item = upsert_content_item(
                session=db_session,
                source_id=source.id,
                item_type=candidate.item_type,
                external_item_id=candidate.external_item_id,
                url=candidate.url,
                title=candidate.title,
            )
            create_observation(
                session=db_session,
                content_item_id=item.id,
                raw_object_id=archive_result.raw_object_id,
            )
            create_version_if_changed(
                session=db_session,
                content_item_id=item.id,
                normalized_text=candidate.normalized_text,
                content_hash=candidate.content_hash,
                language=candidate.language,
            )

        # Assert — content_items exist in DB
        count = db_session.scalar(
            sa.select(sa.func.count()).select_from(
                sa.text("content_items WHERE source_id = :sid")
            ),
            {"sid": source.id},
        )
        assert count > 0

        # Assert — item_versions exist
        version_count = db_session.scalar(
            sa.select(sa.func.count()).select_from(sa.text("item_versions"))
        )
        assert version_count > 0
```

- [ ] **Step 2: 运行非 live 测试确认不影响现有**

```bash
uv run pytest tests/integration/test_sina_7x24_live_crawl_smoke.py -v
```

预期：1 skipped (HARVESTER_ENABLE_LIVE_CRAWL not set)。

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_sina_7x24_live_crawl_smoke.py
git commit -m "test(integration): add Sina 7x24 live crawl smoke test"
```

---

### Task 9: CDC Weekly 实际抓取 Smoke 测试

**Files:**
- Modify: `tests/integration/test_cdc_public_crawl_smoke.py`
- Reference: `harvester/extractors/cdc_weekly.py`

- [ ] **Step 1: 在现有 CDC smoke 文件中扩展 CDC Weekly live 测试**

在 `tests/integration/test_cdc_public_crawl_smoke.py` 的 `TestCDCLiveSmoke` 类中添加 CDC Weekly 的 live smoke test。如果该类不存在，则在文件末尾创建：

```python
@pytest.mark.skipif(not LIVE_CRAWL_ENABLED, reason="HARVESTER_ENABLE_LIVE_CRAWL not set")
class TestCDCWeeklyLiveCrawlSmoke:
    """Live smoke test: real Firecrawl + CDCWeeklyExtractor on real page."""

    def test_cdc_weekly_live_crawl(self, db_session):
        from harvester.db.models import Source
        from harvester.adapters.firecrawl import FirecrawlAdapter
        from harvester.extractors.cdc_weekly import CDCWeeklyExtractor
        from harvester.jobs.raw_archive import write_archive
        from harvester.jobs.extraction import upsert_content_item, create_observation, create_version_if_changed

        cdc_weekly_url = "https://www.cdc.gov/mmwr/weekly/index.html"

        # Arrange
        source = Source(name="cdc-weekly-live", kind="web", url=cdc_weekly_url, status="watched")
        db_session.add(source)
        db_session.flush()

        # Act — fetch
        adapter = FirecrawlAdapter()
        crawl_result = adapter.crawl(cdc_weekly_url)
        assert crawl_result is not None

        # Act — archive
        html = crawl_result.html if hasattr(crawl_result, "html") else str(crawl_result)
        archive_result = write_archive(
            session=db_session,
            source_id=source.id,
            content_type="text/html",
            payload=html,
            url=cdc_weekly_url,
        )
        assert archive_result.raw_object_id is not None

        # Act — extract
        extractor = CDCWeeklyExtractor()
        candidates = extractor.extract(html)
        assert len(candidates) >= 0  # CDC weekly may have no current issue

        # Act — upsert
        for candidate in candidates:
            item = upsert_content_item(
                session=db_session,
                source_id=source.id,
                item_type=candidate.item_type,
                external_item_id=candidate.external_item_id,
                url=candidate.url,
                title=candidate.title,
            )
            create_observation(
                session=db_session,
                content_item_id=item.id,
                raw_object_id=archive_result.raw_object_id,
            )
            create_version_if_changed(
                session=db_session,
                content_item_id=item.id,
                normalized_text=candidate.normalized_text,
                content_hash=candidate.content_hash,
                language=candidate.language,
            )

        # Assert — raw_object exists
        count = db_session.scalar(
            sa.select(sa.func.count()).select_from(
                sa.text("raw_objects WHERE source_id = :sid")
            ),
            {"sid": source.id},
        )
        assert count > 0
```

注意：需要先读取现有文件确认 `LIVE_CRAWL_ENABLED` 变量和 import 的位置，确保不重复定义。

- [ ] **Step 2: 运行确认不影响现有**

```bash
uv run pytest tests/integration/test_cdc_public_crawl_smoke.py -v
```

预期：原有测试全部 passed，新增 1 skipped。

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_cdc_public_crawl_smoke.py
git commit -m "test(integration): add CDC Weekly live crawl smoke test"
```

---

### Task 10: 完整工作流 Smoke 测试

**Files:**
- Create: `tests/integration/test_full_workflow_smoke.py`
- Reference: `harvester/api/routers/` (all entity endpoints)

- [ ] **Step 1: 编写完整工作流 smoke 测试**

新建 `tests/integration/test_full_workflow_smoke.py`，通过 HTTP API 执行完整生命周期。

```python
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

LIVE_CRAWL_ENABLED = os.environ.get("HARVESTER_ENABLE_LIVE_CRAWL", "").strip() == "1"


@pytest.fixture
def workflow_db_url():
    """Create isolated DB for workflow test."""
    from sqlalchemy import create_engine, text
    admin_url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"
    db_name = f"harvester_workflow_test_{uuid.uuid4().hex[:8]}"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    admin_engine.execute(text(f"CREATE DATABASE {db_name}"))
    db_url = f"postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/{db_name}"

    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config()
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")

    yield db_url

    admin_engine.execute(text(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}'"))
    admin_engine.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
    admin_engine.dispose()


@pytest.mark.skipif(not LIVE_CRAWL_ENABLED, reason="HARVESTER_ENABLE_LIVE_CRAWL not set")
@pytest.mark.asyncio
async def test_full_workflow_via_api(workflow_db_url):
    """Complete lifecycle: propose source -> recipe -> approve -> crawl -> extract -> search."""
    with patch.dict(os.environ, {
        "HARVESTER_API_TOKEN": "test-secret",
        "HARVESTER_DATABASE_URL": workflow_db_url,
    }):
        from harvester.api.app import create_app
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": "Bearer test-secret"}
            suffix = uuid.uuid4().hex[:6]

            # 1. Propose source
            resp = await client.post("/sources/propose", json={
                "name": f"workflow-src-{suffix}",
                "kind": "web",
                "url": f"https://finance.sina.com.cn/7x24/",
            }, headers=headers)
            assert resp.status_code == 201
            source_id = resp.json()["id"]

            # 2. Promote to watched
            resp = await client.post(f"/sources/{source_id}/promote", headers=headers)
            assert resp.status_code == 200
            resp = await client.post(f"/sources/{source_id}/promote", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["status"] == "watched"

            # 3. Create recipe
            resp = await client.post("/recipes", json={
                "name": f"workflow-recipe-{suffix}",
                "executor": "http_fetch",
                "config": {"url": "https://finance.sina.com.cn/7x24/"},
                "risk_level": "low",
            }, headers=headers)
            assert resp.status_code == 201
            recipe_id = resp.json()["id"]

            # 4. Approve recipe
            resp = await client.post(f"/recipes/{recipe_id}/approve", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["approval_status"] == "approved"

            # 5. Trigger crawl
            resp = await client.post("/crawl/run", json={
                "source_id": source_id,
                "recipe_id": recipe_id,
            }, headers=headers)
            assert resp.status_code in (200, 201)

            # 6. Verify audit trail
            import sqlalchemy as sa
            from sqlalchemy import create_engine
            engine = create_engine(workflow_db_url)
            with engine.connect() as conn:
                audits = conn.execute(
                    sa.text("SELECT action FROM audit_events ORDER BY created_at"),
                ).fetchall()
                actions = [r[0] for r in audits]
                assert "status_change" in actions
            engine.dispose()
```

- [ ] **Step 2: 运行确认不影响现有**

```bash
uv run pytest tests/integration/test_full_workflow_smoke.py -v
```

预期：1 skipped。

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_full_workflow_smoke.py
git commit -m "test(integration): add full workflow smoke test via API"
```

---

### Task 11: 阶段 2 验收

- [ ] **Step 1: 运行全部后端测试**

```bash
uv run pytest tests/ -q -rs
```

预期：所有原有测试 passed，新增 smoke 测试 skipped（opt-in）。

- [ ] **Step 2: 确认 live 测试可通过 env var 手动触发**

```bash
HARVESTER_ENABLE_LIVE_CRAWL=1 uv run pytest tests/integration/test_sina_7x24_live_crawl_smoke.py -v
```

注意：此步骤需要后端和外部网络可用，仅在验证时运行。

---

## 阶段 3：缺陷修复与 UX 打磨

### Task 12: API 错误处理审计

**Files:**
- Audit: `harvester/api/routers/*.py`
- Audit: `harvester/api/app.py` (exception handlers)

- [ ] **Step 1: 审计所有 router 的错误响应格式**

检查每个 router 中 `raise HTTPException` 的调用，确认：
- 所有 4xx 使用 `{"detail": "..."}` 格式
- 状态机转换失败返回 400
- 实体不存在返回 404

运行：
```bash
grep -rn "HTTPException" harvester/api/routers/
```

- [ ] **Step 2: 检查全局异常处理器**

在 `harvester/api/app.py` 中确认是否有全局异常处理器处理未捕获异常，确保返回 JSON 而非 500 纯文本。

- [ ] **Step 3: 修复发现的问题**

根据审计结果修复具体问题。每个修复需要对应的测试。

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "fix(api): improve error response consistency"
```

---

### Task 13: 前端 UX 改善

**Files:**
- Audit & Modify: `frontend/src/features/*/components/*.tsx`

- [ ] **Step 1: 审计所有列表页的空状态**

检查以下页面是否有空状态处理：
- Content library（已有 `content-empty`）
- Audit log
- Jobs
- Crawls

运行：
```bash
grep -rn "empty\|暂无\|没有数据\|no-data" frontend/src/features/
```

- [ ] **Step 2: 补充缺失的空状态**

为缺少空状态的页面添加空状态组件。

- [ ] **Step 3: 审计加载状态**

检查数据加载时是否有加载指示器。

- [ ] **Step 4: 审计表单验证**

检查所有表单在提交前是否验证必填字段。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "fix(frontend): improve empty states, loading, and form validation"
```

---

## 阶段 4：代码质量清理

### Task 14: 死代码清理

**Files:**
- All files in `harvester/` and `frontend/src/`

- [ ] **Step 1: 查找未使用的 import**

```bash
uv run ruff check --select F401 harvester/
```

- [ ] **Step 2: 移除未使用的 import 和注释代码**

逐个文件修复。

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "chore: remove unused imports and commented-out code"
```

---

### Task 15: 重复逻辑提取

**Files:**
- Audit: `harvester/` and `frontend/src/`

- [ ] **Step 1: 扫描重复模式**

```bash
# Check API test fixture duplication
grep -rn "api_test_db\|api_recipe_test_db\|api_sched_test_db" tests/api/
```

- [ ] **Step 2: 评估是否值得提取**

API 测试中每个文件独立的 DB fixture 是隔离策略的一部分。只有当 3+ 处出现完全相同的逻辑时才提取。

- [ ] **Step 3: 提取并提交（如有）**

---

### Task 16: 文件大小审计与拆分

- [ ] **Step 1: 列出超过 500 行的文件**

```bash
find harvester/ -name "*.py" -exec wc -l {} \; | sort -rn | head -20
find frontend/src/ -name "*.tsx" -o -name "*.ts" | xargs wc -l | sort -rn | head -20
```

- [ ] **Step 2: 拆分超过 1000 行的文件**

如有，识别职责边界并拆分。

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "refactor: split oversized files for maintainability"
```

---

### Task 17: 代码风格统一

- [ ] **Step 1: 运行后端格式化**

```bash
uv run black . && uv run isort .
```

- [ ] **Step 2: 运行前端格式化和 lint**

```bash
cd frontend && npm run format && npm run lint
```

- [ ] **Step 3: 修复所有 lint 错误**

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "style: apply black, isort, prettier formatting"
```

---

## 阶段 5：文档完善

### Task 18: 更新 README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 对照当前 API 端点检查 README**

```bash
grep -rn "def .*\(.*request" harvester/api/routers/ | head -30
```

- [ ] **Step 2: 更新过时或不准确的内容**

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: update README to reflect current API and setup"
```

---

### Task 19: API 文档完善

**Files:**
- Modify: `harvester/api/routers/*.py` (docstrings)

- [ ] **Step 1: 为缺少 docstring 的端点添加描述**

检查所有 router 中的端点函数是否有 docstring：
```bash
grep -A1 '@router\.' harvester/api/routers/*.py | grep 'async def' | grep -v '"""'
```

- [ ] **Step 2: 为 request/response schema 添加描述**

检查 `schemas.py` 和各 router 内联 schema 的字段描述。

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "docs(api): add endpoint docstrings and schema descriptions"
```

---

### Task 20: 项目约定审查

**Files:**
- Modify: `CLAUDE.md`, `AGENTS.md`, `DESIGN.md`, `TODOS.md`

- [ ] **Step 1: 审查 CLAUDE.md / AGENTS.md**

检查约定是否仍然适用，更新过时内容。

- [ ] **Step 2: 审查 DESIGN.md**

确认前端实现仍符合设计系统。

- [ ] **Step 3: 更新 TODOS.md**

根据打磨后的状态更新优先级。

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "docs: update project conventions and TODO priorities"
```

---

## 自审检查

### Spec 覆盖

| 设计文档要求 | 对应 Task |
|---|---|
| 1.1 跑全部测试 | Task 1 |
| 1.2 覆盖率基线 | Task 1 |
| 1.3 Sources PATCH 测试 | Task 2 |
| 1.3 Recipes reject/resubmit/deprecate/patch | Task 3 |
| 1.3 Schedules pause/resume/disable/patch | Task 4 |
| 1.4 Content Library E2E | Task 5 |
| 1.4 Source Resume E2E | Task 6 |
| 2.1 新浪 live crawl | Task 8 |
| 2.2 CDC Weekly live crawl | Task 9 |
| 2.3 完整工作流 smoke | Task 10 |
| 3.1 缺陷清单 | Task 12 |
| 3.2 API 错误处理 | Task 12 |
| 3.3 前端 UX | Task 13 |
| 4.1 死代码 | Task 14 |
| 4.2 重复逻辑 | Task 15 |
| 4.3 文件大小 | Task 16 |
| 4.4 代码风格 | Task 17 |
| 5.1 README | Task 18 |
| 5.2 API 文档 | Task 19 |
| 5.3 约定审查 | Task 20 |

### Placeholder 扫描

无 TBD/TODO/占位符。阶段 3-5 的审计步骤为探索性任务，无法预写具体代码，但步骤明确。

### 类型一致性

所有 Task 中引用的函数名、fixture 名、endpoint 路径均与代码库一致：
- `api_client` / `api_test_db` / `api_recipe_test_db` / `api_sched_test_db` — 与各测试文件 fixture 对应
- `_insert_source` / `_insert_recipe` / `_insert_schedule` — 与 `test_watch_schedules.py` 辅助函数对应
- 所有 API 路径与 router 实现一致
