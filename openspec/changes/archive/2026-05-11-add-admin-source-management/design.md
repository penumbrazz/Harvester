## Context

Source 是 Harvester 的入口对象，已有 propose、promote、pause API，但缺少列表查询、resume/archive API 和前端操作面。这个 change 建立第一个真实业务页面，用来验证 foundation 的 API client、表单、表格、状态 pill 和 E2E 策略。

## Goals / Non-Goals

**Goals:**

- 暴露 source 列表 read API，支持前端筛选和排序需要的字段。
- 补齐前端生命周期操作需要的 resume/archive API，继续通过集中状态机写 audit。
- 实现信息源页面、搜索/筛选、propose 表单和状态操作按钮。
- 使用真实 HTTP E2E 覆盖 source 创建和状态变化。

**Non-Goals:**

- 不实现 recipe/schedule 的完整管理，只显示 source 上的默认 recipe 或 schedule 摘要字段。
- 不直接从前端访问数据库。
- 不新增登录态或细粒度权限。

## Decisions

1. **source 列表使用专门 read API，而不是前端复用 CLI。**
   - 原因：前端必须真实 HTTP 调用后端，CLI 只是另一个客户端。
   - 替代方案：前端调用 CLI 或本地命令。违背浏览器部署模型。

2. **状态变更全部走现有 `transition_entity`。**
   - 原因：状态机、非法 transition 和 audit 必须保持单一路径。
   - 替代方案：router 内直接改 status。实现少，但破坏审计边界。

3. **表格保留密集运维形态，视觉按 `DESIGN.md` 克制处理。**
   - 原因：source 管理是重复操作界面，不适合营销式卡片布局。
   - 替代方案：完全复刻参考 HTML。信息架构可用，但视觉不符合当前要求。

## Risks / Trade-offs

- [Risk] source API 字段过早扩张。→ Mitigation: 第一版只返回列表和操作必要字段，不暴露 raw payload。
- [Risk] archive/resume 语义与状态机不一致。→ Mitigation: 使用 `SOURCE_TRANSITIONS` 并补齐测试。
- [Risk] E2E 依赖真实数据库状态。→ Mitigation: 使用测试 fixture/API 创建隔离数据，禁止 `test.skip()`。
