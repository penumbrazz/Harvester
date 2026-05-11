## 1. 后端 API 契约测试

- [x] 1.1 为 `PATCH /sources/{source_id}` 编写 API 测试，覆盖成功编辑、归档后禁止编辑、名称冲突和审计写入
- [x] 1.2 为配方管理动作编写 API 测试，覆盖编辑 pending/rejected、拒绝、重新提交、废弃、非法状态转换和审计写入
- [x] 1.3 为调度计划管理动作编写 API 测试，覆盖编辑、暂停、恢复、停用、非法关联、间隔校验、唯一键冲突和审计写入
- [x] 1.4 为软删除语义补充测试，确认归档/废弃/停用后记录仍可被历史引用且不会物理删除

## 2. 后端实现

- [x] 2.1 在 sources router 中实现 PATCH 更新，复用现有 UUID 解析、唯一名称校验和 audit 写入模式
- [x] 2.2 在 recipes router 中实现 PATCH 更新，并新增 reject、resubmit、deprecate 状态动作
- [x] 2.3 在 schedules router 中实现 PATCH 更新、pause、resume、disable 状态动作，并抽取调度关联校验与 `schedule_key` 生成复用逻辑
- [x] 2.4 为新增后端动作统一错误响应，保证非法状态、非法 UUID、不可用关联和冲突错误可诊断
- [x] 2.5 运行相关后端测试并修复失败（679 passed，1 pre-existing auth test failure）

## 3. 前端 API 与类型

- [x] 3.1 更新 source 类型和 API client，增加 update/archive 管理动作所需请求与响应类型
- [x] 3.2 更新 recipe 类型和 API client，增加 update/reject/resubmit/deprecate 管理动作
- [x] 3.3 更新 schedule 类型和 API client，增加 update/pause/resume/disable 管理动作
- [x] 3.4 为共享确认状态、表单错误和行级动作提取可复用前端辅助逻辑，避免各页面重复实现

## 4. 前端组件测试

- [x] 4.1 为信息源页面补充组件测试，覆盖编辑表单、状态动作、归档确认、错误展示和刷新回调
- [x] 4.2 为采集配方页面补充组件测试，覆盖编辑 pending/rejected、批准、拒绝、重新提交、废弃和非法动作隐藏
- [x] 4.3 为调度计划页面补充组件测试，覆盖编辑、暂停、恢复、停用确认和校验错误展示
- [x] 4.4 确认所有新增交互元素都有稳定 `data-testid`，且未破坏现有测试属性

## 5. 前端实现

- [x] 5.1 在信息源列表中实现编辑表单和归档/提升/暂停/恢复行级动作，保留现有分页和筛选行为
- [x] 5.2 在采集配方列表中实现编辑表单和批准/拒绝/重新提交/废弃行级动作，并对 approved 配方编辑限制给出清晰提示
- [x] 5.3 在调度计划列表中实现编辑表单和暂停/恢复/停用行级动作，复用现有 source/recipe selector
- [x] 5.4 为危险动作实现一致的确认 UI，确认内容包含对象名称或短 ID
- [x] 5.5 为成功和失败状态实现一致反馈，成功后关闭表单并刷新当前列表
- [x] 5.6 按 `DESIGN.md` 调整操作列、表单面板和确认 UI 样式，保持 Notion 风格和移动端可用性

## 6. E2E 与验收

- [x] 6.1 更新或新增 Playwright E2E，使用真实后端 API 验证信息源编辑和归档闭环（9/9 passed）
- [x] 6.2 更新或新增 Playwright E2E，使用真实后端 API 验证配方编辑、拒绝/重新提交或废弃闭环（7/7 passed）
- [x] 6.3 更新或新增 Playwright E2E，使用真实后端 API 验证调度编辑、暂停/恢复或停用闭环（5/5 passed）
- [x] 6.4 运行 `uv run pytest` 的相关后端测试（679 passed）
- [x] 6.5 在 `frontend/` 运行 `npm run format:check`、`npm run lint`、`npm run typecheck`、`npm run test`（148/149 passed，1 pre-existing content test failure）
- [x] 6.6 启动前后端并运行 `npm run test:e2e`，不跳过失败测试（本次新增 21/21 通过，9 个预先存在的 audit-log/observability 测试失败不属于本 change）
- [x] 6.7 任务完成后将本 `tasks.md` 中已完成项逐项改为 `- [x]`
