## ADDED Requirements

### Requirement: Recipe management
系统 SHALL 在管理控制台提供 recipe 浏览、创建和审批能力。

#### Scenario: List recipes
- **WHEN** 用户打开 Recipes 页面
- **THEN** 系统 MUST 展示 recipe ID、名称、executor、risk level、approval status、version、创建时间和更新时间

#### Scenario: Create recipe
- **WHEN** 用户提交有效 recipe 名称、executor、config、risk level 和 auth profile
- **THEN** 前端 MUST 调用真实 recipe 创建 API，并显示 pending approval 状态

#### Scenario: Approve recipe
- **WHEN** 用户审批 pending recipe
- **THEN** 系统 MUST 通过 HTTP API 将 approval status 转为 approved 并写入 audit event

### Requirement: Watch schedule management
系统 SHALL 在管理控制台提供 watch schedule 浏览和创建能力。

#### Scenario: List schedules
- **WHEN** 用户打开 Schedules 页面
- **THEN** 系统 MUST 展示 schedule key、source、topic、recipe、status、interval、next run、last enqueue、priority、lane 和创建时间

#### Scenario: Create source schedule
- **WHEN** 用户选择 watched source、approved recipe 和合法 interval 创建 schedule
- **THEN** 系统 MUST 创建 active schedule 并显示 next run 时间

#### Scenario: Reject invalid schedule
- **WHEN** 用户选择未 watched 的 source、未 approved 的 recipe 或小于 60 秒的 interval
- **THEN** 系统 MUST 拒绝创建并显示后端错误

### Requirement: Shared selectors
系统 SHALL 为 crawl 和 schedule 流程提供 source、topic 和 approved recipe selector。

#### Scenario: Select approved recipe
- **WHEN** 用户打开需要 recipe 的表单
- **THEN** 前端 MUST 只将 approved recipe 标记为可直接选择，其他状态需显示不可用原因
