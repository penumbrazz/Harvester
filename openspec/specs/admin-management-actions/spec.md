## ADDED Requirements

### Requirement: 信息源可编辑
系统 SHALL 提供信息源字段编辑能力，并通过真实 HTTP API 更新生产数据。

#### Scenario: 成功编辑信息源字段
- **WHEN** 客户端携带有效 API token 调用 `PATCH /sources/{source_id}` 并提交合法的 `name`、`kind`、`url`、`trust_level` 或 `auth_required`
- **THEN** 系统 MUST 更新指定信息源、返回更新后的信息源响应，并写入包含变更前后摘要的审计事件

#### Scenario: 归档信息源禁止编辑
- **WHEN** 客户端调用 `PATCH /sources/{source_id}` 编辑 `status="archived"` 的信息源
- **THEN** 系统 MUST 拒绝请求并保持信息源不变

#### Scenario: 信息源名称冲突被拒绝
- **WHEN** 客户端将信息源名称修改为另一个已存在信息源的名称
- **THEN** 系统 MUST 返回冲突错误，且不能修改原信息源

### Requirement: 信息源状态化删除
系统 SHALL 将信息源删除表达为归档状态变化，而不是物理删除数据库记录。

#### Scenario: 前端归档信息源
- **WHEN** 用户在信息源列表中对可归档信息源确认“归档”
- **THEN** 前端 MUST 通过 Harvester API 将信息源状态变为 `archived`，刷新列表，并显示成功或失败反馈

#### Scenario: 信息源归档保留历史引用
- **WHEN** 信息源被归档
- **THEN** 系统 MUST 保留该信息源记录和既有抓取、内容、作业等长期业务引用，并且归档产生的 audit event MUST 遵循 `audit-log-retention` 保留策略自动清理

### Requirement: 采集配方可编辑
系统 SHALL 允许用户编辑未批准的采集配方，并防止直接修改已批准配方的执行行为。

#### Scenario: 成功编辑 pending 配方
- **WHEN** 客户端携带有效 API token 调用 `PATCH /recipes/{recipe_id}` 编辑 `approval_status="pending"` 的配方字段
- **THEN** 系统 MUST 更新配方、返回更新后的配方响应，并写入审计事件

#### Scenario: 成功编辑 rejected 配方
- **WHEN** 客户端携带有效 API token 调用 `PATCH /recipes/{recipe_id}` 编辑 `approval_status="rejected"` 的配方字段
- **THEN** 系统 MUST 更新配方、保持或恢复其可重新提交状态，并写入审计事件

#### Scenario: 已批准配方禁止直接编辑执行字段
- **WHEN** 客户端调用 `PATCH /recipes/{recipe_id}` 修改 `approval_status="approved"` 配方的 `executor`、`config`、`risk_level` 或 `auth_profile`
- **THEN** 系统 MUST 拒绝请求并提示先废弃旧配方后创建新配方

#### Scenario: 不支持的执行器被拒绝
- **WHEN** 客户端编辑配方并提交不在 approved executor 集合中的 `executor`
- **THEN** 系统 MUST 返回校验错误，且不能修改配方

### Requirement: 采集配方生命周期管理
系统 SHALL 在 API 和前端中暴露批准、拒绝、重新提交和废弃动作。

#### Scenario: 拒绝 pending 配方
- **WHEN** 用户在采集配方列表中对 `approval_status="pending"` 的配方确认“拒绝”
- **THEN** 系统 MUST 将配方状态变为 `rejected`，写入审计事件，并在前端刷新后显示新状态

#### Scenario: 重新提交 rejected 配方
- **WHEN** 用户在采集配方列表中对 `approval_status="rejected"` 的配方执行“重新提交”
- **THEN** 系统 MUST 将配方状态变为 `pending`，写入审计事件，并允许后续批准或继续编辑

#### Scenario: 废弃 approved 配方
- **WHEN** 用户在采集配方列表中对 `approval_status="approved"` 的配方确认“废弃”
- **THEN** 系统 MUST 将配方状态变为 `deprecated`，写入审计事件，并保留历史调度和抓取引用

#### Scenario: 非法配方状态转换被拒绝
- **WHEN** 用户请求不符合 `RECIPE_TRANSITIONS` 的状态变化
- **THEN** 系统 MUST 返回错误、保持配方状态不变，并记录可诊断的失败信息

### Requirement: 调度计划可编辑
系统 SHALL 允许用户编辑调度计划字段，并在关联字段变化时维护调度唯一性。

#### Scenario: 成功编辑调度计划
- **WHEN** 客户端携带有效 API token 调用 `PATCH /schedules/{schedule_id}` 并提交合法的 `source_id`、`topic_watch_id`、`recipe_id`、`interval_seconds`、`priority` 或 `lane`
- **THEN** 系统 MUST 更新调度计划、返回更新后的调度响应，并写入审计事件

#### Scenario: 调度间隔过短被拒绝
- **WHEN** 客户端编辑调度计划并提交小于 60 秒的 `interval_seconds`
- **THEN** 系统 MUST 返回校验错误，且不能修改调度计划

#### Scenario: 调度关联对象不可用被拒绝
- **WHEN** 客户端编辑调度计划并提交不可调度的信息源、未批准的配方或非 active 的 topic watch
- **THEN** 系统 MUST 拒绝请求并保持调度计划不变

#### Scenario: 调度唯一键冲突被拒绝
- **WHEN** 客户端编辑调度计划导致新的 source/recipe/topic 组合与已有调度冲突
- **THEN** 系统 MUST 返回冲突错误，且不能修改调度计划

### Requirement: 调度计划状态化管理
系统 SHALL 支持调度计划暂停、恢复和停用，并将停用作为删除语义。

#### Scenario: 暂停 active 调度
- **WHEN** 用户在调度计划列表中对 `status="active"` 的调度执行“暂停”
- **THEN** 系统 MUST 将调度状态变为 `paused`，写入审计事件，并阻止调度器继续入队该调度

#### Scenario: 恢复 paused 调度
- **WHEN** 用户在调度计划列表中对 `status="paused"` 的调度执行“恢复”
- **THEN** 系统 MUST 将调度状态变为 `active`，写入审计事件，并允许调度器后续入队该调度

#### Scenario: 停用调度作为删除
- **WHEN** 用户在调度计划列表中确认“停用”
- **THEN** 系统 MUST 将调度状态变为 `disabled`，写入审计事件，并保留调度记录及历史引用

#### Scenario: 停用调度禁止编辑
- **WHEN** 客户端调用 `PATCH /schedules/{schedule_id}` 编辑 `status="disabled"` 的调度计划
- **THEN** 系统 MUST 拒绝请求并保持调度计划不变

### Requirement: 前端管理动作交互
系统 SHALL 在管理控制台中为信息源、采集配方和调度计划提供可发现、可确认、可反馈的管理动作。

#### Scenario: 列表显示可用行级动作
- **WHEN** 用户打开信息源、采集配方或调度计划列表页
- **THEN** 前端 MUST 根据当前对象状态显示可执行动作，并隐藏或禁用非法动作

#### Scenario: 编辑表单保留测试属性
- **WHEN** 用户打开任一对象的编辑表单
- **THEN** 前端 MUST 显示当前字段值、提供保存和取消动作，并为交互元素提供稳定的 `data-testid`

#### Scenario: 危险动作需要确认
- **WHEN** 用户执行归档、废弃、停用或拒绝等危险动作
- **THEN** 前端 MUST 在发送 API 请求前显示确认步骤，确认内容 MUST 包含对象名称或短 ID

#### Scenario: 操作失败显示错误
- **WHEN** 管理动作 API 返回错误
- **THEN** 前端 MUST 保持当前页面上下文，显示可读错误信息，并允许用户重新尝试或取消

#### Scenario: 操作成功刷新当前列表
- **WHEN** 管理动作 API 成功返回
- **THEN** 前端 MUST 关闭相关表单或确认状态，刷新当前列表数据，并显示最新对象状态

### Requirement: 管理动作测试覆盖
系统 SHALL 用后端、前端组件和 E2E 测试覆盖新增管理动作。

#### Scenario: 后端 API 测试覆盖管理动作
- **WHEN** 开发者运行相关 Python API 测试
- **THEN** 测试 MUST 覆盖编辑成功、非法状态、校验失败、唯一冲突和审计写入

#### Scenario: 前端组件测试覆盖管理动作
- **WHEN** 开发者运行前端单元/组件测试
- **THEN** 测试 MUST 覆盖动作按钮可见性、编辑表单提交、危险确认、错误展示和列表刷新

#### Scenario: E2E 测试使用真实 HTTP API
- **WHEN** 开发者运行前端 E2E 测试
- **THEN** 测试 MUST 通过真实 Harvester API 验证至少一个信息源、一个配方和一个调度计划的管理动作闭环，且不能使用 `test.skip()` 或静默失败
