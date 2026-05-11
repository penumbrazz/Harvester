## ADDED Requirements

### Requirement: Source list API
系统 SHALL 提供 source 列表 API，返回管理控制台展示和筛选所需字段。

#### Scenario: List sources
- **WHEN** 前端携带有效 API token 请求 source 列表
- **THEN** 系统 MUST 返回 source 的 ID、名称、类型、URL、状态、信任等级、失败计数、创建时间和更新时间

#### Scenario: Filter sources by status and kind
- **WHEN** 用户按状态或类型筛选 source 列表
- **THEN** API 或前端 MUST 只展示匹配条件的 source

### Requirement: Source proposal form
系统 SHALL 允许用户在管理控制台创建 candidate source。

#### Scenario: Propose source successfully
- **WHEN** 用户提交有效名称、类型、URL、信任等级和认证需求
- **THEN** 前端 MUST 调用 `POST /sources/propose` 并在成功后显示新 source 的 candidate 状态

#### Scenario: Duplicate source name
- **WHEN** 后端返回 source 名称冲突
- **THEN** 前端 MUST 显示错误且不伪造成功状态

### Requirement: Source lifecycle actions
系统 SHALL 允许用户通过管理控制台执行合法 source 生命周期操作。

#### Scenario: Promote candidate source
- **WHEN** 用户点击 candidate source 的提升操作
- **THEN** 系统 MUST 通过 HTTP API 将 source 转为 testing 并写入 audit event

#### Scenario: Pause watched source
- **WHEN** 用户点击 watched source 的暂停操作
- **THEN** 系统 MUST 通过 HTTP API 将 source 转为 paused 并写入 audit event

#### Scenario: Reject illegal transition
- **WHEN** 用户或前端请求非法 source 状态变化
- **THEN** 系统 MUST 拒绝请求、显示错误，并保持原状态

### Requirement: Source management E2E uses real API
系统 SHALL 用真实 HTTP API 验证信息源页面关键流程。

#### Scenario: E2E creates and promotes source
- **WHEN** E2E 测试在浏览器中创建 source 并点击提升
- **THEN** 测试 MUST 观察到真实后端返回的新状态，且不得 mock 后端 API
