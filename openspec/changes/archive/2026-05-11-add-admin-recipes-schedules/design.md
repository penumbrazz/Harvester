## Context

Recipe 定义如何抓取/抽取，WatchSchedule 定义何时持续抓取。当前已有创建 recipe、审批 recipe、创建 schedule 的 API，但缺少列表和选择器。这个 change 让用户不用复制 UUID 就能配置持续采集。

## Goals / Non-Goals

**Goals:**

- 增加 recipe 和 schedule 列表 read API。
- 实现 recipe 创建、审批、列表筛选和 approved recipe selector。
- 实现 schedule 创建、列表筛选和 source/topic/recipe 关联表单。
- 前端通过真实 API 校验 recipe approval 与 source schedulable 状态。

**Non-Goals:**

- 不实现 recipe 编辑、版本 diff、回滚或复制。
- 不实现 schedule pause/resume/delete，除非后端已有安全状态机。
- 不引入高风险 recipe 沙箱、登录态或浏览器 profile。

## Decisions

1. **recipes 和 schedules 独立成管理页面。**
   - 原因：它们是持续采集配置，不应隐藏在 source 页面里。
   - 替代方案：只放在 source 详情。第一版无 source 详情页，会影响可发现性。

2. **schedule 表单必须使用真实 selector。**
   - 原因：减少 UUID 复制错误，并让前端可以展示不可调度原因。
   - 替代方案：保留纯 UUID 输入。实现更快，但运维体验差。

3. **第一版只做创建和审批，不做破坏性 schedule 操作。**
   - 原因：暂停/删除 recurring ingestion 需要清晰 audit 和恢复语义。
   - 替代方案：直接删除 schedule。风险高且不符合审计优先。

## Risks / Trade-offs

- [Risk] recipe config JSON 表单复杂。→ Mitigation: 第一版使用 JSON textarea + 校验反馈，后续再做 executor-specific form。
- [Risk] schedule 创建依赖 source/topic/recipe 状态。→ Mitigation: 后端保持最终校验，前端只做提示。
- [Risk] recipes/schedules 与 operations 页面选择器重复。→ Mitigation: 抽出共享 selector 组件。
