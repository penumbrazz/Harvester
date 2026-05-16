# 内容库详情弹窗 & 来源筛选 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为内容库新增内容详情弹窗（点击条目查看元数据+完整正文）和来源筛选下拉框。

**Architecture:** 后端新增 `GET /items/content/{id}` API 返回 content_item 元数据及最新 ItemVersion 正文；前端新建 `ContentDetailModal` 组件，在 `ContentLibraryPage` 中管理选中状态，点击行/卡片时打开弹窗按需加载详情。来源筛选复用已有 `listSources` API 填充下拉选项。

**Tech Stack:** FastAPI (后端), React + TypeScript (前端), Vitest + Testing Library (前端测试), pytest + httpx (后端测试)

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `harvester/api/routers/content_items.py` | 新增 `GET /items/content/{id}` 详情端点及 response schema |
| Modify | `tests/api/test_content_items.py` | 新增详情 API 测试 |
| Modify | `tests/utils/factories.py` | 扩展 `insert_item_version` 支持 `normalized_text` 和 `language` 参数 |
| Modify | `frontend/src/types/content.ts` | 新增 `ContentDetailResponse`、`ItemVersionSummary` 类型 |
| Modify | `frontend/src/lib/content-api.ts` | 新增 `getContentItemDetail` 函数 |
| Create | `frontend/src/features/content/content-detail-modal.tsx` | 详情弹窗组件 |
| Modify | `frontend/src/features/content/content-library-page.tsx` | 集成弹窗 + 来源筛选 + 行/卡片点击 |
| Modify | `frontend/src/features/content/__tests__/content-library-page.test.tsx` | 新增弹窗和来源筛选测试 |

---

### Task 1: 扩展 `insert_item_version` 工厂函数支持 `normalized_text` 和 `language`

**Files:**
- Modify: `tests/utils/factories.py:74-85`

- [ ] **Step 1: Write the failing test**

在 `tests/utils/factories.py` 中暂时不做修改。先在 `tests/api/test_content_items.py` 末尾添加一个使用 `normalized_text` 参数的测试，它将因为工厂函数不支持该参数而失败。

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_content_items.py -v -k "test_content_detail_returns_latest_version"`
Expected: FAIL — `insert_item_version() got an unexpected keyword argument 'normalized_text'`

- [ ] **Step 3: Write minimal implementation**

修改 `tests/utils/factories.py` 中的 `insert_item_version` 函数，添加 `normalized_text` 和 `language` 可选参数：

```python
def insert_item_version(
    session: Session,
    content_item_id: uuid.UUID,
    *,
    normalized_text: str | None = None,
    language: str | None = None,
) -> uuid.UUID:
    """Insert an item_version row and return its id."""
    iv_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO item_versions "
            "(id, content_item_id, content_hash, normalized_text, language, created_at) "
            "VALUES (:id, :ci_id, :hash, :text, :lang, :ts)"
        ),
        {
            "id": iv_id,
            "ci_id": content_item_id,
            "hash": uuid.uuid4().hex,
            "text": normalized_text,
            "lang": language,
            "ts": _now(),
        },
    )
    return iv_id
```

- [ ] **Step 4: Run existing tests to verify no regression**

Run: `uv run pytest tests/api/test_content_items.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add tests/utils/factories.py
git commit -m "test: extend insert_item_version factory to support normalized_text and language"
```

---

### Task 2: 后端 — 新增 `GET /items/content/{id}` 详情 API

**Files:**
- Modify: `harvester/api/routers/content_items.py:1-107`
- Modify: `tests/api/test_content_items.py`

- [ ] **Step 1: Write the failing test**

在 `tests/api/test_content_items.py` 末尾添加以下测试：

```python
# --- Content detail endpoint ---


@pytest.mark.asyncio
async def test_content_detail_returns_item_with_version(
    content_api_client, content_test_db
):
    """GET /items/content/{id} should return item metadata + latest version text."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "detail-src")
        ci_id = insert_content_item(
            session,
            src_id,
            "Detail Test Article",
            canonical_url="https://example.com/detail",
        )
        insert_item_version(
            session,
            ci_id,
            normalized_text="Full article body text here.",
            language="en",
        )
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content/{ci_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(ci_id)
    assert data["title"] == "Detail Test Article"
    assert data["source_name"] == "detail-src"
    assert data["latest_version"] is not None
    assert data["latest_version"]["normalized_text"] == "Full article body text here."
    assert data["latest_version"]["language"] == "en"


@pytest.mark.asyncio
async def test_content_detail_returns_null_version_when_no_version(
    content_api_client, content_test_db
):
    """GET /items/content/{id} should return latest_version as null when no versions exist."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "no-version-src")
        ci_id = insert_content_item(session, src_id, "No Version Article")
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content/{ci_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["latest_version"] is None


@pytest.mark.asyncio
async def test_content_detail_returns_404_for_missing_id(content_api_client):
    """GET /items/content/{id} should return 404 for non-existent id."""
    fake_id = uuid.uuid4()
    response = await content_api_client.get(
        f"/items/content/{fake_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_content_detail_returns_latest_of_multiple_versions(
    content_api_client, content_test_db
):
    """GET /items/content/{id} should return the most recent version."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "multi-version-src")
        ci_id = insert_content_item(session, src_id, "Multi Version Article")
        insert_item_version(
            session, ci_id, normalized_text="First version text", language="en"
        )
        insert_item_version(
            session, ci_id, normalized_text="Second version text", language="en"
        )
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content/{ci_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    # Should return the most recently created version
    assert data["latest_version"]["normalized_text"] == "Second version text"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_content_items.py -v -k "content_detail"`
Expected: FAIL — 404 or route not found

- [ ] **Step 3: Write minimal implementation**

在 `harvester/api/routers/content_items.py` 中新增 response schema 和详情端点。在文件末尾追加：

```python
from harvester.db.models import ContentItem, ItemVersion, Source


class ItemVersionResponse(BaseModel):
    """Item version summary for detail view."""

    id: str
    normalized_text: str | None = None
    language: str | None = None
    content_hash: str
    created_at: datetime


class ContentDetailResponse(BaseModel):
    """Full content item detail with latest version."""

    id: str
    item_type: str
    title: str | None = None
    canonical_url: str | None = None
    status: str
    source_name: str | None = None
    created_at: datetime
    updated_at: datetime
    latest_version: ItemVersionResponse | None = None


@router.get("/content/{content_item_id}", response_model=ContentDetailResponse)
def get_content_item_detail(
    content_item_id: UUID,
    _token: str = _Token,
    session: Session = _Session,
):
    """Get a single content item with its latest version text."""
    row = (
        session.query(ContentItem, Source.name.label("source_name"))
        .outerjoin(Source, ContentItem.source_id == Source.id)
        .filter(ContentItem.id == content_item_id)
        .first()
    )
    if row is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Content item not found")

    content_item = row.ContentItem
    source_name = row.source_name

    latest_version = (
        session.query(ItemVersion)
        .filter(ItemVersion.content_item_id == content_item_id)
        .order_by(ItemVersion.created_at.desc())
        .first()
    )

    return ContentDetailResponse(
        id=str(content_item.id),
        item_type=content_item.item_type,
        title=content_item.title,
        canonical_url=content_item.canonical_url,
        status=content_item.status,
        source_name=source_name,
        created_at=content_item.created_at,
        updated_at=content_item.updated_at,
        latest_version=(
            ItemVersionResponse(
                id=str(latest_version.id),
                normalized_text=latest_version.normalized_text,
                language=latest_version.language,
                content_hash=latest_version.content_hash,
                created_at=latest_version.created_at,
            )
            if latest_version
            else None
        ),
    )
```

注意：需要将 `ItemVersion` 添加到文件顶部的 import 行：

```python
from harvester.db.models import ContentItem, ItemVersion, Source
```

同时把 `HTTPException` 添加到 fastapi import：

```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_content_items.py -v -k "content_detail"`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite to verify no regression**

Run: `uv run pytest tests/api/test_content_items.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add harvester/api/routers/content_items.py tests/api/test_content_items.py
git commit -m "feat(api): add GET /items/content/{id} detail endpoint with latest version"
```

---

### Task 3: 前端 — 新增 TypeScript 类型定义和 API 函数

**Files:**
- Modify: `frontend/src/types/content.ts`
- Modify: `frontend/src/lib/content-api.ts`

- [ ] **Step 1: Add types to `frontend/src/types/content.ts`**

在文件末尾追加：

```typescript
/** Item version summary from the backend detail endpoint. */
export interface ItemVersionSummary {
  id: string
  normalized_text: string | null
  language: string | null
  content_hash: string
  created_at: string
}

/** Content item detail response from GET /items/content/{id}. */
export interface ContentDetailResponse {
  id: string
  item_type: string
  title: string | null
  canonical_url: string | null
  status: string
  source_name: string | null
  created_at: string
  updated_at: string
  latest_version: ItemVersionSummary | null
}
```

- [ ] **Step 2: Add API function to `frontend/src/lib/content-api.ts`**

在文件顶部的 import 中添加 `ContentDetailResponse`：

```typescript
import type {
  ContentDetailResponse,
  ContentListResponse,
  SearchMode,
  SearchResponse,
} from '../types/content'
```

在文件末尾追加：

```typescript
/** Fetch a single content item detail with latest version text. */
export function getContentItemDetail(
  config: ApiConfig,
  contentItemId: string,
): Promise<ContentDetailResponse> {
  return apiRequest<ContentDetailResponse>(config, `/items/content/${contentItemId}`)
}
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/content.ts frontend/src/lib/content-api.ts
git commit -m "feat(frontend): add ContentDetailResponse type and getContentItemDetail API"
```

---

### Task 4: 前端 — 创建 `ContentDetailModal` 组件

**Files:**
- Create: `frontend/src/features/content/content-detail-modal.tsx`

- [ ] **Step 1: Create the modal component**

创建 `frontend/src/features/content/content-detail-modal.tsx`：

```tsx
import { useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { ContentDetailResponse } from '../../types/content'
import { CONTENT_STATUS_LABELS, CONTENT_STATUS_VARIANTS } from '../../types/content'
import { StatusPill } from '../../components/ui/status-pill'
import { getContentItemDetail } from '../../lib/content-api'
import { formatDate } from '../../lib/format'

interface ContentDetailModalProps {
  config: ApiConfig
  contentItemId: string | null
  onClose: () => void
}

export function ContentDetailModal({
  config,
  contentItemId,
  onClose,
}: ContentDetailModalProps) {
  const [detail, setDetail] = useState<ContentDetailResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!contentItemId) {
      setDetail(null)
      return
    }
    setLoading(true)
    setError('')
    getContentItemDetail(config, contentItemId)
      .then((data) => setDetail(data))
      .catch((err) => setError(err instanceof Error ? err.message : '加载详情失败'))
      .finally(() => setLoading(false))
  }, [config, contentItemId])

  useEffect(() => {
    if (!contentItemId) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [contentItemId, onClose])

  if (!contentItemId) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.4)',
        zIndex: 100,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        data-testid="content-detail-modal"
        style={{
          background: '#ffffff',
          borderRadius: 12,
          width: '100%',
          maxWidth: 720,
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid rgba(0,0,0,0.1)',
          boxShadow:
            'rgba(0,0,0,0.01) 0px 1px 3px, rgba(0,0,0,0.02) 0px 3px 7px, rgba(0,0,0,0.02) 0px 7px 15px, rgba(0,0,0,0.04) 0px 14px 28px, rgba(0,0,0,0.05) 0px 23px 52px',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            padding: '20px 24px 16px',
            borderBottom: '1px solid rgba(0,0,0,0.1)',
            flexShrink: 0,
          }}
        >
          <div style={{ flex: 1, marginRight: 16 }}>
            <h3
              style={{
                fontFamily: 'var(--font-family)',
                fontSize: 22,
                fontWeight: 700,
                margin: '0 0 8px',
                lineHeight: 1.27,
                letterSpacing: '-0.25px',
                color: 'rgba(0,0,0,0.95)',
              }}
            >
              {loading ? ' ' : detail?.title || '无标题'}
            </h3>
            {!loading && detail && (
              <div
                style={{
                  display: 'flex',
                  gap: 8,
                  alignItems: 'center',
                  flexWrap: 'wrap',
                }}
              >
                <StatusPill variant="default">{detail.item_type}</StatusPill>
                <StatusPill
                  variant={CONTENT_STATUS_VARIANTS[detail.status] || 'default'}
                >
                  {CONTENT_STATUS_LABELS[detail.status] || detail.status}
                </StatusPill>
                {detail.source_name && (
                  <span
                    style={{
                      fontSize: 12,
                      color: '#615d59',
                    }}
                  >
                    {detail.source_name}
                  </span>
                )}
              </div>
            )}
          </div>
          <button
            data-testid="close-content-detail-button"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 20,
              cursor: 'pointer',
              color: '#a39e98',
              padding: '4px 8px',
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* Meta info */}
        {!loading && detail && (
          <div
            style={{
              padding: '12px 24px',
              borderBottom: '1px solid rgba(0,0,0,0.1)',
              flexShrink: 0,
            }}
          >
            {detail.canonical_url && (
              <a
                href={detail.canonical_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#0075de',
                  textDecoration: 'none',
                  fontSize: 13,
                  display: 'block',
                  marginBottom: 4,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {detail.canonical_url}
              </a>
            )}
            <div
              style={{
                fontSize: 12,
                color: '#a39e98',
              }}
            >
              创建于 {formatDate(detail.created_at)}
              {' / '}
              更新于 {formatDate(detail.updated_at)}
            </div>
          </div>
        )}

        {/* Body */}
        <div
          data-testid="content-detail-body"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px 24px',
            minHeight: 0,
          }}
        >
          {loading && (
            <div style={{ color: '#615d59', fontSize: 14 }}>加载中...</div>
          )}
          {error && (
            <div style={{ color: '#dd5b00', fontSize: 14 }}>{error}</div>
          )}
          {!loading && !error && detail?.latest_version?.normalized_text && (
            <div
              style={{
                fontSize: 15,
                lineHeight: 1.6,
                color: 'rgba(0,0,0,0.95)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {detail.latest_version.normalized_text}
            </div>
          )}
          {!loading && !error && detail && !detail.latest_version && (
            <div style={{ color: '#a39e98', fontSize: 14 }}>暂无正文内容</div>
          )}
          {!loading && !error && detail?.latest_version && !detail.latest_version.normalized_text && (
            <div style={{ color: '#a39e98', fontSize: 14 }}>暂无正文内容</div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/content/content-detail-modal.tsx
git commit -m "feat(frontend): create ContentDetailModal component"
```

---

### Task 5: 前端 — 集成弹窗和来源筛选到内容库页面

**Files:**
- Modify: `frontend/src/features/content/content-library-page.tsx`

- [ ] **Step 1: Add source filter state and fetching**

在 `content-library-page.tsx` 的 import 区域添加：

```typescript
import { ContentDetailModal } from './content-detail-modal'
import { listSources } from '../../lib/source-api'
import type { Source } from '../../types/source'
```

在组件 state 区域（约 line 43）添加来源筛选 state：

```typescript
const [sourceFilter, setSourceFilter] = useState('')
const [sources, setSources] = useState<Source[]>([])
const [selectedItemId, setSelectedItemId] = useState<string | null>(null)
```

添加来源列表加载 effect（在现有的 `fetchContent` effect 之后）：

```typescript
useEffect(() => {
  if (!config.baseUrl) return
  listSources(config, { limit: 100 })
    .then((data) => setSources(data.items))
    .catch(() => setSources([]))
}, [config])
```

- [ ] **Step 2: Pass source_id to listContentItems**

修改 `fetchContent` 函数，添加 `source_id` 参数：

```typescript
const data = await listContentItems(config, {
  status: statusFilter || undefined,
  item_type: typeFilter || undefined,
  source_id: sourceFilter || undefined,
  limit: PAGE_SIZE,
  offset,
})
```

将 `sourceFilter` 加入 `fetchContent` 的依赖数组：

```typescript
}, [config, statusFilter, typeFilter, sourceFilter, offset])
```

更新 `hasActiveFilters`：

```typescript
const hasActiveFilters = statusFilter !== '' || typeFilter !== '' || sourceFilter !== ''
```

- [ ] **Step 3: Add source filter Select to filter bar**

在筛选栏中状态筛选 Select 后面、view toggle 前面，插入来源筛选：

```tsx
<Select
  data-testid="select-source-filter"
  value={sourceFilter}
  onChange={(e) => {
    setSourceFilter(e.target.value)
    setOffset(0)
  }}
>
  <option value="">全部来源</option>
  {sources.map((s) => (
    <option key={s.id} value={s.id}>
      {s.name}
    </option>
  ))}
</Select>
```

- [ ] **Step 4: Make ContentRow and ContentCard clickable**

将 `ContentRow` 修改为接受 `onClick` prop：

```tsx
function ContentRow({
  item,
  onClick,
}: {
  item: ContentItem
  onClick: () => void
}) {
  return (
    <tr
      style={{
        borderBottom: 'var(--border-whisper)',
        cursor: 'pointer',
      }}
      onClick={onClick}
      onMouseEnter={(e) => {
        ;(e.currentTarget as HTMLElement).style.background = '#f6f5f4'
      }}
      onMouseLeave={(e) => {
        ;(e.currentTarget as HTMLElement).style.background = ''
      }}
    >
      {/* existing td cells unchanged */}
    </tr>
  )
}
```

更新 ContentRow 调用处：

```tsx
{items.map((item) => (
  <ContentRow
    key={item.id}
    item={item}
    onClick={() => setSelectedItemId(item.id)}
  />
))}
```

将 `ContentCard` 修改为接受 `onClick` prop：

```tsx
function ContentCard({
  item,
  onClick,
}: {
  item: ContentItem
  onClick: () => void
}) {
  return (
    <Card
      style={{
        padding: 'var(--space-4)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
        cursor: 'pointer',
      }}
      onClick={onClick}
    >
      {/* existing content unchanged */}
    </Card>
  )
}
```

更新 ContentCard 调用处：

```tsx
{items.map((item) => (
  <ContentCard
    key={item.id}
    item={item}
    onClick={() => setSelectedItemId(item.id)}
  />
))}
```

- [ ] **Step 5: Add modal to render output**

在 `ContentLibraryPage` 的 return JSX 最外层 `<div>` 末尾，`</div>` 之前添加弹窗：

```tsx
<ContentDetailModal
  config={config}
  contentItemId={selectedItemId}
  onClose={() => setSelectedItemId(null)}
/>
```

- [ ] **Step 6: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/content/content-library-page.tsx
git commit -m "feat(frontend): integrate detail modal and source filter into content library"
```

---

### Task 6: 前端测试 — 详情弹窗和来源筛选

**Files:**
- Modify: `frontend/src/features/content/__tests__/content-library-page.test.tsx`

- [ ] **Step 1: Write tests for source filter**

在 `content-library-page.test.tsx` 末尾追加：

```typescript
describe('ContentLibraryPage - source filter', () => {
  it('renders source filter dropdown', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({
          items: [
            {
              id: 'src-1',
              name: 'TechBlog',
              kind: 'rss',
              status: 'watched',
              url: null,
              trust_level: 'medium',
              failure_count: 0,
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z',
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        })
      }
      return mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 })
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-source-filter')).toBeInTheDocument()
    })

    expect(screen.getByText('TechBlog')).toBeInTheDocument()
  })

  it('sends source_id filter to the API', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({
          items: [
            {
              id: 'src-1',
              name: 'TechBlog',
              kind: 'rss',
              status: 'watched',
              url: null,
              trust_level: 'medium',
              failure_count: 0,
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z',
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-source-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-source-filter'), 'src-1')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('source_id=src-1'),
        expect.any(Object),
      )
    })
  })
})
```

- [ ] **Step 2: Write tests for content detail modal**

在同一文件末尾追加：

```typescript
describe('ContentLibraryPage - content detail modal', () => {
  it('opens modal when a content row is clicked', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Understanding TypeScript Generics'))

    await waitFor(() => {
      expect(screen.getByTestId('content-detail-modal')).toBeInTheDocument()
    })
  })

  it('closes modal when close button is clicked', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      if (url.includes('/items/content/ci-1')) {
        return mockJsonResponse({
          id: 'ci-1',
          item_type: 'article',
          title: 'Understanding TypeScript Generics',
          canonical_url: 'https://example.com/ts-generics',
          status: 'active',
          source_name: 'TechBlog',
          created_at: '2026-01-01T10:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
          latest_version: {
            id: 'iv-1',
            normalized_text: 'Full text of the article.',
            language: 'en',
            content_hash: 'abc123',
            created_at: '2026-01-01T11:00:00Z',
          },
        })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Understanding TypeScript Generics'))

    await waitFor(() => {
      expect(screen.getByTestId('content-detail-modal')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('close-content-detail-button'))

    await waitFor(() => {
      expect(screen.queryByTestId('content-detail-modal')).not.toBeInTheDocument()
    })
  })

  it('displays full article text in modal', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      if (url.includes('/items/content/ci-1')) {
        return mockJsonResponse({
          id: 'ci-1',
          item_type: 'article',
          title: 'Understanding TypeScript Generics',
          canonical_url: 'https://example.com/ts-generics',
          status: 'active',
          source_name: 'TechBlog',
          created_at: '2026-01-01T10:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
          latest_version: {
            id: 'iv-1',
            normalized_text: 'This is the full article body text that was previously hidden.',
            language: 'en',
            content_hash: 'abc123',
            created_at: '2026-01-01T11:00:00Z',
          },
        })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Understanding TypeScript Generics'))

    await waitFor(() => {
      expect(screen.getByTestId('content-detail-body')).toHaveTextContent(
        'This is the full article body text that was previously hidden.',
      )
    })
  })
})
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npm test -- --run`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/content/__tests__/content-library-page.test.tsx
git commit -m "test(frontend): add tests for source filter and content detail modal"
```

---

### Task 7: 格式化和最终验证

**Files:** 无新增

- [ ] **Step 1: Run backend formatter and linter**

Run: `uv run ruff format . && uv run ruff check --fix .`
Expected: No errors

- [ ] **Step 2: Run frontend formatter and linter**

Run: `cd frontend && npm run format && npm run lint`
Expected: No errors

- [ ] **Step 3: Run full backend test suite**

Run: `uv run pytest tests/api/test_content_items.py -v`
Expected: ALL PASS

- [ ] **Step 4: Run full frontend test suite**

Run: `cd frontend && npm test -- --run`
Expected: ALL PASS

- [ ] **Step 5: Manual smoke test**

Run: `./start.sh`
1. 打开 `http://localhost:5173`，导航到内容库
2. 确认筛选栏出现了来源下拉
3. 点击一个内容条目，确认弹窗打开并显示正文
4. 确认关闭按钮、遮罩层点击、Escape 键都能关闭弹窗
