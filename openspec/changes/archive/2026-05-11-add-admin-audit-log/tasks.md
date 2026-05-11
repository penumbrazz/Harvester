## 1. API Tests

- [x] 1.1 编写 audit event list API 测试，覆盖认证、字段、倒序排序和分页
- [x] 1.2 编写 entity_type、entity_id、action、actor、时间范围筛选测试
- [x] 1.3 编写不返回 raw payload 的断言测试

## 2. Backend Implementation

- [x] 2.1 新增 audit router 和 audit event list endpoint
- [x] 2.2 实现筛选、分页、倒序排序和 before/after state 摘要序列化
- [x] 2.3 确认 audit 查询不改变数据库状态，也不绕过 API token

## 3. Frontend Tests

- [x] 3.1 编写审计日志页面测试，覆盖时间线、筛选、加载更多、空状态和错误状态
- [x] 3.2 编写 entity-specific filter 测试，覆盖按实体查看相关 audit events
- [x] 3.3 编写真 HTTP E2E，使用真实状态变更产生 audit event 后在页面查询

## 4. Frontend Implementation

- [x] 4.1 新增 audit API 类型和 client 方法
- [x] 4.2 实现审计日志页面、筛选栏、时间线、状态摘要和加载更多
- [x] 4.3 为 source/crawl/job/content 页面预留按 entity 跳转到 audit 过滤视图的路由参数
- [x] 4.4 确保 before/after state 展示有长度限制且不泄漏 raw payload

## 5. Verification

- [x] 5.1 运行 audit API 测试和现有 source 状态机 audit 回归测试
- [x] 5.2 运行前端 lint、类型检查、单元/组件测试和真实 HTTP E2E
- [x] 5.3 手动验证审计日志按时间倒序、筛选准确、视觉符合 `DESIGN.md`
