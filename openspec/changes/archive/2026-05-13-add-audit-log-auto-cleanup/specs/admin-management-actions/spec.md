## MODIFIED Requirements

### Requirement: 信息源状态化删除
系统 SHALL 将信息源删除表达为归档状态变化，而不是物理删除数据库记录。

#### Scenario: 前端归档信息源
- **WHEN** 用户在信息源列表中对可归档信息源确认“归档”
- **THEN** 前端 MUST 通过 Harvester API 将信息源状态变为 `archived`，刷新列表，并显示成功或失败反馈

#### Scenario: 信息源归档保留历史引用
- **WHEN** 信息源被归档
- **THEN** 系统 MUST 保留该信息源记录和既有抓取、内容、作业等长期业务引用，并且归档产生的 audit event MUST 遵循 `audit-log-retention` 保留策略自动清理
