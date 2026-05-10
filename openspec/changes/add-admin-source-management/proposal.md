## Why

信息源是 Harvester 控制面的入口对象，但当前只能通过 CLI/API 执行 propose、promote、pause 等动作，缺少可浏览、筛选和操作的管理界面。需要把 source 生命周期做成第一个业务纵向切片，验证前端 foundation 能真实驱动后端状态机。

## What Changes

- 新增 source 列表 read API，返回 ID、名称、类型、URL、状态、信任等级、失败计数、默认 recipe、创建/更新时间等前端需要的字段。
- 新增 source 状态操作所需 API 覆盖：propose、promote、pause、resume、archive；所有状态变更继续走集中状态机和 audit。
- 新增信息源管理页面：搜索、状态筛选、类型筛选、生命周期展示、列表表格、状态 pill、操作按钮和错误反馈。
- 新增 propose source 表单，提交真实 `POST /sources/propose`，不 mock 后端 API。
- 保留 `data-testid`，覆盖列表、筛选、表单和状态操作 E2E。
- 视觉必须遵循根目录 `DESIGN.md`，不沿用参考 HTML 的厚边框/游戏化风格。

## Capabilities

### New Capabilities

- `admin-source-management`: 管理控制台的信息源列表、筛选、创建和状态生命周期操作能力。

### Modified Capabilities

- 无。

## Impact

- 后端新增或扩展 `harvester/api/routers/sources.py` 的 read/status endpoints。
- 前端新增 source feature 模块、API 类型、页面路由和 E2E。
- 测试新增 API 单元/集成测试和前端真实 HTTP E2E。
- 依赖 `add-admin-console-foundation` 提供前端工程、API client、布局和设计 token。
