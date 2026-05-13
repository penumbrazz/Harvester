### Requirement: 审计日志默认短保留
系统 SHALL 默认只保留最近 7 天的 audit events。

#### Scenario: 使用默认保留窗口
- **WHEN** 系统未配置自定义审计日志保留天数
- **THEN** 审计清理 MUST 使用 7 天作为 retention window

#### Scenario: 保留窗口内事件不被删除
- **WHEN** audit event 的 `created_at` 位于当前时间向前 7 天以内
- **THEN** 审计清理 MUST 保留该 audit event

#### Scenario: 超过保留窗口的事件被删除
- **WHEN** audit event 的 `created_at` 早于当前时间向前 7 天的 cutoff
- **THEN** 审计清理 MUST 删除该 audit event

### Requirement: 审计日志保留天数可配置
系统 SHALL 允许运维通过配置覆盖 audit event 保留天数。

#### Scenario: 通过环境变量覆盖保留窗口
- **WHEN** `HARVESTER_AUDIT_RETENTION_DAYS` 被设置为合法正整数
- **THEN** 审计清理 MUST 使用该值计算 cutoff

#### Scenario: 非法保留配置被拒绝
- **WHEN** `HARVESTER_AUDIT_RETENTION_DAYS` 为空值、非整数或小于 1
- **THEN** 系统 MUST 拒绝启动对应清理配置或返回明确错误，且不能用非法值执行删除

### Requirement: 审计清理不影响非审计数据
系统 SHALL 限定审计清理只删除过期 audit events。

#### Scenario: 清理保留业务实体
- **WHEN** 审计清理删除过期 audit events
- **THEN** 系统 MUST 保留 source、topic watch、recipe、schedule、crawl run、job、raw object、content item、item version 和 chunk 记录

#### Scenario: 清理不删除 raw evidence metadata
- **WHEN** 过期 audit event 引用了 raw object 或 crawl run
- **THEN** 审计清理 MUST 只删除 audit event，并保留 raw object metadata、hash、storage URI 和 crawl run 记录

### Requirement: 审计清理可诊断
系统 SHALL 返回或记录审计清理结果，便于运维和测试验证。

#### Scenario: 清理返回统计
- **WHEN** 审计清理运行完成
- **THEN** 系统 MUST 提供 `deleted_count`、`cutoff` 和 `retention_days`

#### Scenario: 无过期事件时返回零删除
- **WHEN** 没有 audit events 早于 cutoff
- **THEN** 审计清理 MUST 返回 `deleted_count=0` 且不能修改未过期事件

### Requirement: 审计清理由后台自动执行
系统 SHALL 在后台 daemon 启用时自动执行审计日志清理。

#### Scenario: Scheduler daemon 触发清理
- **WHEN** scheduler daemon 正常运行
- **THEN** 系统 MUST 按配置的清理间隔自动调用审计清理

#### Scenario: 清理失败不阻断调度
- **WHEN** 自动审计清理发生可恢复错误
- **THEN** scheduler daemon MUST 记录错误、继续处理调度轮次，并允许后续轮次重试清理
