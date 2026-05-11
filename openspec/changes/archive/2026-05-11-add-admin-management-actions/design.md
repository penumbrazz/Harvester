## Context

Harvester 管理控制台已经具备 React/Vite 前端、API 配置、列表页、分页、搜索和部分新增入口，但核心对象的管理动作不完整。当前后端能力也不对称：信息源已有 promote/pause/resume/archive 状态动作，但缺少字段编辑；采集配方只有创建、批准和列表；调度计划只有创建和列表。结果是前端用户只能查看和新增，无法纠错、暂停、废弃或停用对象。

本 change 采用软删除/状态化删除。信息源通过归档删除，采集配方通过废弃删除，调度计划通过停用删除。这样可以保留抓取记录、作业、内容项和审计事件中的历史引用，符合 Harvester 控制平面和 evidence-first 架构的约束。

## Goals / Non-Goals

**Goals:**

- 让信息源、采集配方和调度计划都具备可用的编辑与状态化管理动作。
- 所有前端状态变更都通过真实 HTTP API 完成，不直接写数据库。
- 所有字段更新和状态变化都写入审计事件，记录 before/after 摘要。
- 前端提供清晰的行级动作、编辑表单、危险动作确认、错误提示和刷新后的状态同步。
- 保留并新增必要的 `data-testid`，覆盖组件测试和 E2E 测试。

**Non-Goals:**

- 不实现硬删除，不从生产数据库物理删除信息源、配方或调度计划。
- 不实现内容项、抓取任务、作业队列或审计日志的编辑/删除。
- 不新增复杂权限模型；仍沿用现有 API token 认证。
- 不重做整体视觉系统；页面样式继续遵循 `DESIGN.md` 的 Notion 风格。
- 不引入新的前端状态管理库或 UI 组件库。

## Decisions

### 1. 删除语义使用状态动作，不做硬删除

信息源删除映射为归档，配方删除映射为废弃，调度删除映射为停用。后端可以保留现有 action endpoint 风格，例如 `POST /sources/{id}/archive`，并为缺失对象补齐对应动作。前端按钮文案应使用“归档”“废弃”“停用”，必要时在确认文案中说明这是软删除。

替代方案是添加真正的 `DELETE` endpoint。该方案更符合 REST 直觉，但会让用户误解为物理删除，且容易破坏历史引用；因此不采用。

### 2. 字段编辑使用 PATCH endpoint

新增 `PATCH /sources/{id}`、`PATCH /recipes/{id}` 和 `PATCH /schedules/{id}`。请求体只包含允许修改的字段，后端按对象规则验证，成功后返回更新后的资源。

- 信息源允许编辑 `name`、`kind`、`url`、`trust_level`、`auth_required`。归档信息源不可编辑。
- 调度计划允许编辑 `source_id`、`recipe_id`、`topic_watch_id`、`interval_seconds`、`priority`、`lane`，并在关联字段变化时重新计算唯一 `schedule_key`。停用调度不可编辑。
- 采集配方允许编辑 pending 或 rejected 配方的 `name`、`executor`、`config`、`risk_level`、`auth_profile`。approved 配方不直接修改执行内容，应先废弃后新建，避免正在使用的调度在用户不知情的情况下改变行为。

替代方案是只在前端实现编辑表单，提交到现有 create endpoint 生成新对象。该方案不能解决纠错问题，也不能表达管理动作，因此不采用。

### 3. 配方生命周期补齐为可审计状态机

复用现有 `RECIPE_TRANSITIONS`：`pending -> approved/rejected`、`rejected -> pending`、`approved -> deprecated`。新增 reject、resubmit 和 deprecate API。废弃 approved 配方时，已有调度不被自动删除，但前端需要提醒用户检查关联调度；后端后续可在调度执行侧阻止使用废弃配方。

替代方案是允许 approved 配方原地编辑并递增 `version`。现有 schema 没有 recipe revision 表，原地编辑会让历史调度引用同一个 recipe id 却代表不同执行逻辑，审计和排障成本更高，因此不采用。

### 4. 前端采用行级动作和内嵌/弹层编辑

各列表页在“操作”列提供明确动作：

- 信息源：编辑、提升、暂停、恢复、归档。
- 采集配方：编辑、批准、拒绝、重新提交、废弃。
- 调度计划：编辑、暂停、恢复、停用。

编辑使用页面内面板或轻量弹层，复用现有 Input、Select、Button、StatusPill 基础组件。危险动作必须有确认步骤，确认文案包含对象名称或短 ID，避免误操作。操作成功后关闭表单、清除错误、刷新当前页。

替代方案是新增详情页。详情页更适合深层排障，但当前痛点是列表管理动作缺失；先补行级动作能用最小改动完成闭环。

### 5. 测试按 API 契约和用户工作流覆盖

后端测试覆盖成功、非法状态、字段校验、唯一冲突、审计写入。前端测试覆盖编辑表单、危险确认、动作按钮可见性、成功刷新和错误展示。E2E 使用真实 HTTP 请求，不 mock 后端 API，不允许跳过。

## Risks / Trade-offs

- 配方 approved 状态不可编辑执行字段 → 用户需要通过废弃旧配方并新建配方完成变更；前端文案和错误提示必须解释原因。
- 调度关联字段变更会触发 `schedule_key` 重算 → 后端必须检查冲突，避免两个调度映射到同一 source/recipe/topic 组合。
- 状态化删除不会释放唯一名称 → 如果用户想用同名对象重新创建，后端需要明确返回冲突；后续可单独设计“复制/重建”能力。
- 行级动作增加页面复杂度 → 使用一致的操作列、确认组件和表单布局控制复杂度，避免每页各自实现一套交互。

## Migration Plan

1. 优先复用现有字段和状态值；如调度停用需要新增状态，只通过代码状态值和测试覆盖，不新增数据库列。
2. 增量新增 API endpoint，保持现有 create/list/status action endpoint 可用。
3. 前端 API client 先扩展，再替换页面操作。
4. 运行 Python API 测试、前端单元测试、lint/typecheck 和 E2E。
5. 回滚时可移除新增前端动作并保留后端新增 endpoint；不会破坏现有只读/新增流程。

## Open Questions

无。删除语义已确认采用软删除/状态化删除。
