## Why

当前管理控制台更接近只读列表：信息源、采集配方和调度计划缺少编辑、停用、废弃、归档等管理动作，用户无法在前端完成日常运维闭环。Harvester 是带审计和历史证据链的控制平面，因此需要以状态化删除替代硬删除，既补齐管理能力，又保留抓取、审计和关联记录的可追溯性。

## What Changes

- 为信息源提供编辑入口，并在前端明确暴露提升、暂停、恢复、归档等已有生命周期动作。
- 为采集配方提供编辑、批准、拒绝、重新提交、废弃等生命周期动作，避免只能新增和批准。
- 为调度计划提供编辑、暂停、恢复、停用等状态化管理动作，避免只能新增和查看。
- 后端新增缺失的管理 API，并为所有状态变化和关键字段更新写入审计事件。
- 前端列表页增加行级操作、编辑表单、危险操作确认、成功/失败反馈和刷新后的列表状态同步。
- 删除语义采用软删除/状态化删除：信息源归档、配方废弃、调度停用，不做破坏历史引用的硬删除。

## Capabilities

### New Capabilities

- `admin-management-actions`: 管理控制台对信息源、采集配方和调度计划的编辑与状态化管理能力，包括真实 HTTP API、前端交互、审计和测试契约。

### Modified Capabilities

无。

## Impact

- 后端 API：`harvester/api/routers/sources.py`、`harvester/api/routers/recipes.py`、`harvester/api/routers/schedules.py`。
- 前端 API client：`frontend/src/lib/source-api.ts`、`frontend/src/lib/recipe-api.ts`、`frontend/src/lib/schedule-api.ts`。
- 前端页面：`frontend/src/features/sources/`、`frontend/src/features/recipes-schedules/` 及共享表单/确认组件。
- 类型定义：`frontend/src/types/source.ts`、`frontend/src/types/recipe.ts`、`frontend/src/types/schedule.ts`。
- 测试：相关 Python API 测试、React 组件测试和 Playwright E2E 测试。
- 数据库：优先复用现有字段和状态机；如需新增调度状态或审计字段，必须通过迁移实现。
