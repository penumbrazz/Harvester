## 1. 测试先行

- [x] 1.1 新增 `tests/domain/test_audit_retention.py`，覆盖默认 7 天 retention、环境变量覆盖、非法保留天数和 cutoff 边界
- [x] 1.2 新增审计清理数据安全测试，证明过期 audit events 被删除，但 source、recipe、schedule、crawl run、job、raw object、content item、item version 和 chunk 不被删除
- [x] 1.3 新增 scheduler daemon 集成测试，覆盖自动调用审计清理、清理间隔节流和清理失败不阻断调度轮次
- [x] 1.4 更新现有 `admin-management-actions` 相关测试或新增 spec 对应测试，明确归档业务记录保留但 audit events 遵循 retention 策略

## 2. 审计清理核心实现

- [x] 2.1 新增 audit retention 配置读取，默认 `HARVESTER_AUDIT_RETENTION_DAYS=7`，并拒绝非正整数配置
- [x] 2.2 新增独立审计清理服务，按 `audit_events.created_at < cutoff` 删除过期记录并返回 `deleted_count`、`cutoff`、`retention_days`
- [x] 2.3 确保审计清理只作用于 `audit_events`，不触发非审计表级联删除或业务状态变化
- [x] 2.4 为清理服务补充必要的日志，记录保留天数、cutoff 和删除数量

## 3. 后台自动清理

- [x] 3.1 在 scheduler daemon 维护阶段接入审计清理，复用现有 daemon 生命周期，不新增常驻进程
- [x] 3.2 实现默认 24 小时清理节流，避免 scheduler 每轮都执行 DELETE
- [x] 3.3 处理清理异常：记录错误、回滚当前清理事务，并继续执行或完成 scheduler 轮次
- [x] 3.4 确认 `./start.sh` 的 `HARVESTER_START_DAEMONS=1` 路径启动 scheduler 后可触发自动清理，无需新增默认服务

## 4. 配置与文档

- [x] 4.1 在 `.env.example` 或现有部署配置样例中加入 `HARVESTER_AUDIT_RETENTION_DAYS=7`
- [x] 4.2 如存在运维文档或 README 配置说明，补充审计日志默认 7 天保留和覆盖方式
- [x] 4.3 检查现有审计日志 API 文档或前端文案，避免承诺 audit events 无限期保留

## 5. 验证

- [x] 5.1 运行 `uv run pytest tests/domain/test_audit_retention.py -q`
- [x] 5.2 运行 `uv run pytest tests/jobs/test_scheduler_daemon.py tests/api/test_audit.py tests/api/test_sources.py -q`
- [x] 5.3 运行与 OpenSpec 相关的校验命令，确认 `add-audit-log-auto-cleanup` 的 proposal、design、specs 和 tasks 可被识别
