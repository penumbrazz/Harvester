## Context

Harvester 前端有 7 个列表页面，其中 5 个缺少分页。当前情况：

| 页面 | 后端分页 | 前端分页 UI |
|------|---------|------------|
| Content Library | ✅ limit/offset → `{items, total, limit, offset}` | ✅ 内联翻页按钮 |
| Audit Log | ✅ limit/offset → `{items, total}` | ✅ Load More |
| Crawls | ✅ limit/offset → `{items, total}` | ❌ 仅显示总数 |
| Jobs | ✅ limit/offset → `{items, total}` | ❌ 仅显示总数 |
| Sources | ❌ 返回扁平数组 | ❌ 无 |
| Recipes | ❌ 返回扁平数组 | ❌ 无 |
| Schedules | ❌ 返回扁平数组 | ❌ 无 |

Content Library 的分页 UI 直接内联在页面中，未抽取为可复用组件。

## Goals / Non-Goals

**Goals:**
- 统一所有列表 API 的分页响应格式为 `{ items, total, limit, offset }`
- 为 Sources、Recipes、Schedules 后端 API 添加 limit/offset 参数支持
- 为 Sources、Recipes、Schedules、Crawls、Jobs 前端页面添加分页控件
- 提取可复用的 PaginationControls 组件，替代 Content Library 的内联实现

**Non-Goals:**
- 不改变 Audit Log 的 Load More 模式（功能已完整）
- 不改变 Content Library 的现有分页逻辑，仅替换为共享组件
- 不添加游标分页或无限滚动
- 不涉及 Dashboard 页面（仅展示 5 条最近失败记录的摘要视图）

## Decisions

### D1: 统一分页响应格式为 `{ items, total, limit, offset }`

采用与 Content Library API 一致的四字段响应格式。

**替代方案：** 仅返回 `{ items, total }`（Crawls/Jobs 当前格式）——不采用，因为前端需要知道服务端实际使用的 limit/offset 以正确计算页码。

**影响：** Crawls 和 Jobs 的 `CrawlRunListResponse` / `JobListResponse` 需添加 `limit` 和 `offset` 字段。

### D2: 创建可复用 PaginationControls 组件

Props: `{ total, offset, pageSize, onPageChange: (offset: number) => void }`

渲染逻辑：上一页/下一页按钮 + "X-Y of Z" 计数器。当 `total <= pageSize` 时不渲染。

放置位置：`frontend/src/components/common/pagination-controls.tsx`

### D3: 后端分页参数默认值

- `limit` 默认 20，范围 1-100
- `offset` 默认 0，范围 >= 0

与现有 Crawls/Jobs API 的约定保持一致。

### D4: 前端状态管理模式

每个列表页面独立管理 `offset` state，使用固定的 `PAGE_SIZE = 20` 常量。筛选条件变更时重置 offset 为 0。

不引入全局分页状态管理或 URL query 参数同步——数据量尚不需要复杂的分页策略。

## Risks / Trade-offs

- **[BREAKING CHANGE]** Sources/Recipes/Schedules API 响应格式从扁平数组变为对象 → 前端调用方必须同步更新。缓解：前后端在同一个 PR 中同步发布。
- **[性能]** 每次分页请求都执行 `query.count()` → 对于大数据量可能有性能影响。缓解：当前数据量小，后续可添加估算计数或缓存。
- **[一致性]** Audit Log 使用 Load More 模式，其余页面使用翻页模式 → 用户需适应两种模式。缓解：两种模式适用于不同场景，暂不统一。
