# 信息源名称显示改进

**日期**: 2026-05-17
**状态**: 待实施

## 背景

在抓取任务（crawl runs）、作业队列（jobs）、调度计划（schedules）和搜索结果页面中，信息源列显示的是 UUID 前 8 位（如 `a3f1b2c4`），用户无法直观辨识是哪个信息源。只有内容库（content items）页面通过后端 JOIN 正确显示了 `source_name`。

## 目标

将所有显示 `source_id` 片段的页面改为显示可读的信息源名称，与内容库页面保持一致。

## 方案

采用后端 SQL JOIN 方案，与现有 `content_items` 端点的模式完全一致。在各端点查询中 `outerjoin(Source)` 并在响应中增加 `source_name` 字段。

## 后端改动

### 1. Crawl Runs (`harvester/api/routers/crawl.py`)

- `CrawlRunItem` schema 增加 `source_name: str | None = None`
- `GET /crawl/runs` 查询增加 `outerjoin(Source, CrawlRun.source_id == Source.id)`
- 序列化时从 join 结果取 `Source.name`

### 2. Jobs (`harvester/api/routers/queue.py`)

- `JobItem` schema 增加 `source_name: str | None = None`
- `GET /queue/jobs` 查询增加 `outerjoin(Source, Job.source_id == Source.id)`
- 序列化时从 join 结果取 `Source.name`

### 3. Schedules (`harvester/api/routers/schedules.py`)

- `ScheduleResponse` schema 增加 `source_name: str | None = None`
- `GET /schedules` 和 `GET /schedules/{id}` 查询增加 `outerjoin(Source, Schedule.source_id == Source.id)`
- 序列化时从 join 结果取 `Source.name`

### 4. Search (`harvester/api/routers/search.py`)

- `SearchItem` schema 增加 `source_name: str | None = None`
- 搜索查询增加对 Source 的 join
- 序列化时从 join 结果取 `Source.name`

## 前端改动

所有改动都是将 `source_id.slice(0, 8)` 替换为 `source_name || '--'`。

### 1. CrawlsPage (`frontend/src/features/operations/crawls-page.tsx`)

- 信息源列：显示 `run.source_name || '--'`
- 更新 TypeScript 类型定义增加 `source_name`

### 2. JobsPage (`frontend/src/features/operations/jobs-page.tsx`)

- 信息源列：显示 `job.source_name || '--'`
- 更新 TypeScript 类型定义增加 `source_name`

### 3. ScheduleRow (`frontend/src/features/recipes-schedules/components/schedule-row.tsx`)

- 信息源列：显示 `schedule.source_name || '--'`
- 更新 TypeScript 类型定义增加 `source_name`

### 4. 搜索结果 (`frontend/src/features/content/content-library-page.tsx`)

- 搜索结果信息源列：显示 `item.source_name || '-'`
- 更新 TypeScript 类型定义增加 `source_name`

## 测试

- 后端：为 4 个端点增加/更新集成测试，验证当 source 存在时返回正确的 `source_name`，当 source 不存在时返回 `null`
- 前端：更新 E2E 测试中对信息源列的断言，从验证 UUID 片段改为验证 source 名称
